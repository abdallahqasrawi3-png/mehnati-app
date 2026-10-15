from urllib.parse import quote

from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from catalog.models import BusinessProfile, Offer
from reviews.models import Review, refresh_business_rating
from suppliers.models import Material, SupplierProfile

from .audit import audit
from .models import AbuseReport, ContactMessage
from .permissions import IsPlatformAdmin

TARGET_MODELS = {
    "review": Review,
    "offer": Offer,
    "business": BusinessProfile,
    "material": Material,
    "supplier": SupplierProfile,
}


def _target_summary(target_type, target_id):
    model = TARGET_MODELS.get(target_type)
    obj = model.objects.filter(pk=target_id).first() if model else None
    if obj is None:
        return None
    if target_type == "review":
        return {"text": obj.comment, "rating": obj.rating, "hidden": obj.is_hidden, "business": obj.business.name}
    if target_type in ("business", "supplier"):
        return {"name": obj.name, "status": obj.status}
    return {"title": obj.title, "deleted": obj.is_deleted, "available": obj.is_available}


class AbuseReportSerializer(serializers.ModelSerializer):
    target_type_display = serializers.CharField(source="get_target_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    target = serializers.SerializerMethodField()

    class Meta:
        model = AbuseReport
        fields = [
            "id", "target_type", "target_type_display", "target_id", "reason", "status", "status_display",
            "admin_note", "target", "created_at", "resolved_at",
        ]
        read_only_fields = ["status", "admin_note", "created_at", "resolved_at"]

    def get_target(self, obj):
        return _target_summary(obj.target_type, obj.target_id)

    def validate(self, attrs):
        model = TARGET_MODELS[attrs["target_type"]]
        if not model.objects.filter(pk=attrs["target_id"]).exists():
            raise ValidationError({"target_id": "المحتوى المبلّغ عنه غير موجود."})
        return attrs


class AbuseReportViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Any signed-in user can report content; users see only their own reports."""

    serializer_class = AbuseReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AbuseReport.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class AdminAbuseReportViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AbuseReportSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        qs = AbuseReport.objects.all()
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """body: {decision: resolved|dismissed, hide_content: bool, note: str}"""
        report = AbuseReport.objects.get(pk=pk)
        decision = request.data.get("decision")
        if decision not in (AbuseReport.Status.RESOLVED, AbuseReport.Status.DISMISSED):
            raise ValidationError({"decision": "القرار يجب أن يكون resolved أو dismissed."})
        hide = bool(request.data.get("hide_content")) and decision == AbuseReport.Status.RESOLVED
        if hide:
            model = TARGET_MODELS[report.target_type]
            obj = model.objects.filter(pk=report.target_id).first()
            if obj is not None:
                if report.target_type == "review":
                    obj.is_hidden = True
                    obj.save(update_fields=["is_hidden"])
                    refresh_business_rating(obj.business)
                elif report.target_type in ("business", "supplier"):
                    obj.status = "suspended"
                    obj.save(update_fields=["status"])
                else:
                    obj.is_available = False
                    obj.is_deleted = True
                    obj.save(update_fields=["is_available", "is_deleted"])
        report.status = decision
        report.admin_note = str(request.data.get("note", ""))[:1000]
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save()
        audit(request.user, "resolve_abuse_report", report, decision=decision, hide_content=hide)
        return Response(AbuseReportSerializer(report).data)


class AdminProfileStatusViewSet(viewsets.ViewSet):
    """Suspend / reactivate business and supplier profiles."""

    permission_classes = [IsPlatformAdmin]

    @action(detail=False, methods=["post"], url_path=r"(?P<kind>business|supplier)/(?P<pid>\d+)")
    def set_status(self, request, kind=None, pid=None):
        model = BusinessProfile if kind == "business" else SupplierProfile
        obj = model.objects.filter(pk=pid).first()
        if obj is None:
            raise ValidationError({"detail": "غير موجود."})
        new = request.data.get("status")
        if new not in ("active", "suspended"):
            raise ValidationError({"status": "active أو suspended"})
        obj.status = new
        obj.save(update_fields=["status"])
        audit(request.user, f"set_{kind}_status", obj, status=new, reason=request.data.get("reason", ""))
        return Response({"id": obj.pk, "name": obj.name, "status": obj.status})

    @action(detail=False, methods=["get"], url_path="profiles")
    def profiles(self, request):
        data = [
            {"kind": "business", "id": b.pk, "name": b.name, "owner": b.owner.email, "status": b.status}
            for b in BusinessProfile.objects.select_related("owner").order_by("-created_at")[:200]
        ] + [
            {"kind": "supplier", "id": s.pk, "name": s.name, "owner": s.owner.email, "status": s.status}
            for s in SupplierProfile.objects.select_related("owner").order_by("-created_at")[:200]
        ]
        return Response(data)


# ---------------------------------------------------------------- contact the administrator
class ContactMessageSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True, default=None)

    class Meta:
        model = ContactMessage
        fields = [
            "id", "name", "phone", "email", "kind", "kind_display", "order_ref", "message",
            "status", "status_display", "admin_note", "created_at", "resolved_at",
        ]
        read_only_fields = ["status", "admin_note", "created_at", "resolved_at"]

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("اكتب تفاصيل البلاغ (10 أحرف على الأقل).")
        return value

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("اكتب اسمك.")
        return value


def whatsapp_text(msg):
    lines = [
        "📢 بلاغ جديد من تطبيق مهنتي",
        f"رقم البلاغ: #{msg.pk}",
        f"النوع: {msg.get_kind_display()}",
        f"الاسم: {msg.name}",
    ]
    if msg.phone:
        lines.append(f"الهاتف: {msg.phone}")
    if msg.user_id:
        lines.append(f"البريد: {msg.user.email}")
    if msg.order_ref:
        lines.append(f"رقم الطلب: {msg.order_ref}")
    lines += ["", "التفاصيل:", msg.message]
    return "\n".join(lines)


class ContactAdminView(APIView):
    """Anyone (visitor or signed-in user) can send a report to the administrator.
    The report is saved, and the response carries a WhatsApp link with the details pre-filled."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def post(self, request):
        ser = ContactMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        msg = ser.save(user=user)
        return Response({
            "id": msg.pk,
            "detail": f"تم استلام بلاغك رقم #{msg.pk}.",
            "whatsapp_url": f"https://wa.me/{settings.ADMIN_WHATSAPP}?text={quote(whatsapp_text(msg))}",
        }, status=201)


class AdminContactMessageViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ContactMessageSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        qs = ContactMessage.objects.select_related("user")
        st = self.request.query_params.get("status")
        return qs.filter(status=st) if st else qs

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        msg = ContactMessage.objects.get(pk=pk)
        msg.status = ContactMessage.Status.RESOLVED
        msg.admin_note = str(request.data.get("note", ""))[:1000]
        msg.resolved_at = timezone.now()
        msg.save(update_fields=["status", "admin_note", "resolved_at"])
        audit(request.user, "resolve_contact_message", msg)
        return Response(ContactMessageSerializer(msg).data)

from django.db import IntegrityError, transaction
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from notifications.models import Notification
from notifications.service import notify
from orders.models import SalesOrder

from .models import Review, refresh_business_rating


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    order = serializers.PrimaryKeyRelatedField(queryset=SalesOrder.objects.all())
    items = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "order", "business", "rating", "comment", "customer_name", "items", "created_at", "updated_at"]
        read_only_fields = ["business", "created_at", "updated_at"]

    def get_customer_name(self, obj):
        # Show first name only to protect privacy
        return (obj.customer.full_name or "عميل").split()[0]

    def get_items(self, obj):
        return [i.title for i in obj.order.items.all()]

    def validate_rating(self, v):
        if not 1 <= v <= 5:
            raise serializers.ValidationError("التقييم من 1 إلى 5.")
        return v


class ReviewViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Public list per business. Customers create one review per completed order and may edit
    their own review. Business owners cannot edit or delete reviews (they can report them)."""

    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "patch"]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Review.objects.filter(is_hidden=False).select_related("customer", "order").prefetch_related("order__items")
        if self.action == "list":
            b = self.request.query_params.get("business")
            if b:
                qs = qs.filter(business_id=b)
            if self.request.query_params.get("mine") and self.request.user.is_authenticated:
                qs = qs.filter(customer=self.request.user)
            return qs
        return qs.filter(customer=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        if order.customer_id != self.request.user.pk:
            raise PermissionDenied("يمكنك تقييم طلباتك فقط.")
        if order.status != SalesOrder.Status.COMPLETED:
            raise ValidationError({"order": "يمكن التقييم بعد اكتمال الطلب فقط."})
        try:
            with transaction.atomic():
                review = serializer.save(customer=self.request.user, business=order.business)
        except IntegrityError:
            raise ValidationError({"order": "قيّمت هذا الطلب مسبقًا."})
        refresh_business_rating(order.business)
        notify(order.business.owner, Notification.Kind.REVIEW, "تقييم جديد",
               f"حصلت على تقييم {review.rating} من 5 على الطلب #{order.pk}.", "sales_order", order.pk)

    def perform_update(self, serializer):
        serializer.validated_data.pop("order", None)
        review = serializer.save()
        refresh_business_rating(review.business)

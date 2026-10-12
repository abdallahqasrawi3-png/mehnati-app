from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasBusinessProfile
from inventory import service as stock
from inventory.serializers import MovementSerializer, StockAdjustSerializer

from .models import BusinessImage, BusinessProfile, Category, Offer, OfferImage, ProfileStatus
from .search import public_offers, search_offers
from .serializers import (
    BusinessOwnerSerializer,
    BusinessPublicSerializer,
    CategorySerializer,
    ImageSerializer,
    ImageUploadSerializer,
    OfferOwnerSerializer,
    OfferPublicSerializer,
)

MAX_IMAGES = 8


class ReadOnlyOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrStaff]
    pagination_class = None

    def get_queryset(self):
        qs = Category.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_active=True)
        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return qs


class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    """Public browsing and search (no sign-in required)."""

    serializer_class = OfferPublicSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.action == "list":
            return search_offers(self.request.query_params)
        return public_offers()

    @action(detail=False, methods=["get"])
    def compare(self, request):
        ids = [int(x) for x in request.query_params.get("ids", "").split(",") if x.strip().isdigit()][:4]
        if len(ids) < 2:
            raise ValidationError({"ids": "اختر عرضين على الأقل للمقارنة."})
        offers = list(public_offers().filter(pk__in=ids))
        data = OfferPublicSerializer(offers, many=True, context={"request": request}).data
        units = {o.price_unit for o in offers}
        return Response({
            "offers": data,
            "same_unit": len(units) == 1,
            "note": None if len(units) == 1 else "وحدات السعر مختلفة؛ قارن مع الانتباه لوحدة كل عرض.",
        })


class BusinessViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BusinessPublicSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = BusinessProfile.objects.filter(status=ProfileStatus.ACTIVE).select_related("category", "city", "area")
        p = self.request.query_params
        if p.get("city"):
            qs = qs.filter(city_id=p["city"])
        if p.get("category"):
            qs = qs.filter(category_id=p["category"])
        if p.get("q"):
            from .search import keyword_q

            qs = qs.filter(keyword_q(p["q"], ["name", "description"]))
        return qs.order_by("-rating_avg", "-created_at")


class MyBusinessView(APIView):
    """The signed-in user's own business profile."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        bp = getattr(request.user, "business_profile", None)
        if bp is None:
            return Response({"detail": "لا يوجد ملف مشروع."}, status=404)
        return Response(BusinessOwnerSerializer(bp, context={"request": request}).data)

    def post(self, request):
        if hasattr(request.user, "business_profile"):
            return Response({"detail": "لديك ملف مشروع بالفعل."}, status=400)
        ser = BusinessOwnerSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save(owner=request.user)
        return Response(ser.data, status=201)

    def patch(self, request):
        bp = getattr(request.user, "business_profile", None)
        if bp is None:
            return Response({"detail": "لا يوجد ملف مشروع."}, status=404)
        ser = BusinessOwnerSerializer(bp, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class MyBusinessImagesView(APIView):
    permission_classes = [HasBusinessProfile]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        bp = request.user.business_profile
        if bp.work_images.count() >= MAX_IMAGES * 2:
            return Response({"detail": "وصلت إلى الحد الأعلى لصور الأعمال."}, status=400)
        ser = ImageUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        img = BusinessImage.objects.create(business=bp, image=ser.validated_data["image"])
        return Response(ImageSerializer(img, context={"request": request}).data, status=201)

    def delete(self, request, image_id=None):
        img = get_object_or_404(BusinessImage, pk=image_id, business=request.user.business_profile)
        img.image.delete(save=False)
        img.delete()
        return Response(status=204)


class MyBusinessLogoView(APIView):
    permission_classes = [HasBusinessProfile]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ser = ImageUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        bp = request.user.business_profile
        bp.logo = ser.validated_data["image"]
        bp.save(update_fields=["logo"])
        return Response(BusinessOwnerSerializer(bp, context={"request": request}).data)


class MyOfferViewSet(viewsets.ModelViewSet):
    """Owner manages own offers. Ownership is enforced by the queryset."""

    serializer_class = OfferOwnerSerializer
    permission_classes = [HasBusinessProfile]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return (
            Offer.objects.filter(business=self.request.user.business_profile, is_deleted=False)
            .select_related("category")
            .prefetch_related("images")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        initial = serializer.validated_data.pop("initial_stock", 0) or 0
        offer = serializer.save(business=self.request.user.business_profile)
        if initial and offer.tracks_stock:
            stock.adjust(offer, initial, actor=self.request.user, note="الكمية الأولية")
            offer.refresh_from_db()

    def perform_update(self, serializer):
        serializer.validated_data.pop("initial_stock", None)
        serializer.save()

    def perform_destroy(self, instance):
        # Soft delete: keeps history of existing orders intact; hides it from the public.
        instance.is_deleted = True
        instance.is_available = False
        instance.save(update_fields=["is_deleted", "is_available", "updated_at"])

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def images(self, request, pk=None):
        offer = self.get_object()
        if offer.images.count() >= MAX_IMAGES:
            return Response({"detail": f"الحد الأعلى {MAX_IMAGES} صور لكل عرض."}, status=400)
        ser = ImageUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        img = OfferImage.objects.create(offer=offer, image=ser.validated_data["image"], sort_order=offer.images.count())
        return Response(ImageSerializer(img, context={"request": request}).data, status=201)

    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>\d+)")
    def delete_image(self, request, pk=None, image_id=None):
        offer = self.get_object()
        img = get_object_or_404(OfferImage, pk=image_id, offer=offer)
        img.image.delete(save=False)
        img.delete()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def stock(self, request, pk=None):
        offer = self.get_object()
        ser = StockAdjustSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        stock.adjust(offer, ser.validated_data["delta"], actor=request.user, note=ser.validated_data.get("note", ""))
        offer.refresh_from_db()
        return Response(self.get_serializer(offer).data)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        offer = self.get_object()
        return Response(MovementSerializer(offer.movements.all()[:100], many=True).data)

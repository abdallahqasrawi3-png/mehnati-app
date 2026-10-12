from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import ProfileStatus
from catalog.search import public_materials, search_materials
from catalog.serializers import ImageSerializer, ImageUploadSerializer
from core.permissions import HasSupplierProfile
from inventory import service as stock
from inventory.serializers import MovementSerializer, StockAdjustSerializer

from .models import Material, MaterialImage, SupplierProfile
from .serializers import (
    MaterialOwnerSerializer,
    MaterialPublicSerializer,
    SupplierOwnerSerializer,
    SupplierPublicSerializer,
)


class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SupplierPublicSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = SupplierProfile.objects.filter(status=ProfileStatus.ACTIVE).select_related("city", "area")
        if self.request.query_params.get("city"):
            qs = qs.filter(city_id=self.request.query_params["city"])
        return qs


class MaterialViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MaterialPublicSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.action == "list":
            return search_materials(self.request.query_params)
        return public_materials()

    @action(detail=False, methods=["get"])
    def compare(self, request):
        ids = [int(x) for x in request.query_params.get("ids", "").split(",") if x.strip().isdigit()][:4]
        if len(ids) < 2:
            raise ValidationError({"ids": "اختر مادتين على الأقل للمقارنة."})
        items = list(public_materials().filter(pk__in=ids))
        units = {m.unit for m in items}
        return Response({
            "materials": MaterialPublicSerializer(items, many=True, context={"request": request}).data,
            "same_unit": len(units) == 1,
            "note": None if len(units) == 1 else "وحدات القياس مختلفة (مثل المتر والقطعة)؛ الأسعار غير قابلة للمقارنة المباشرة.",
        })


class MySupplierView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sp = getattr(request.user, "supplier_profile", None)
        if sp is None:
            return Response({"detail": "لا يوجد ملف مورد."}, status=404)
        return Response(SupplierOwnerSerializer(sp, context={"request": request}).data)

    def post(self, request):
        if hasattr(request.user, "supplier_profile"):
            return Response({"detail": "لديك ملف مورد بالفعل."}, status=400)
        ser = SupplierOwnerSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save(owner=request.user)
        return Response(ser.data, status=201)

    def patch(self, request):
        sp = getattr(request.user, "supplier_profile", None)
        if sp is None:
            return Response({"detail": "لا يوجد ملف مورد."}, status=404)
        ser = SupplierOwnerSerializer(sp, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class MyMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialOwnerSerializer
    permission_classes = [HasSupplierProfile]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return (
            Material.objects.filter(supplier=self.request.user.supplier_profile, is_deleted=False)
            .select_related("category")
            .prefetch_related("images")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        initial = serializer.validated_data.pop("initial_stock", 0) or 0
        m = serializer.save(supplier=self.request.user.supplier_profile)
        if initial:
            stock.adjust(m, initial, actor=self.request.user, note="الكمية الأولية")

    def perform_update(self, serializer):
        serializer.validated_data.pop("initial_stock", None)
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.is_available = False
        instance.save(update_fields=["is_deleted", "is_available", "updated_at"])

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def images(self, request, pk=None):
        m = self.get_object()
        if m.images.count() >= 8:
            return Response({"detail": "الحد الأعلى 8 صور لكل مادة."}, status=400)
        ser = ImageUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        img = MaterialImage.objects.create(material=m, image=ser.validated_data["image"], sort_order=m.images.count())
        return Response(ImageSerializer(img, context={"request": request}).data, status=201)

    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>\d+)")
    def delete_image(self, request, pk=None, image_id=None):
        m = self.get_object()
        img = get_object_or_404(MaterialImage, pk=image_id, material=m)
        img.image.delete(save=False)
        img.delete()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def stock(self, request, pk=None):
        m = self.get_object()
        ser = StockAdjustSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        stock.adjust(m, ser.validated_data["delta"], actor=request.user, note=ser.validated_data.get("note", ""))
        m.refresh_from_db()
        return Response(self.get_serializer(m).data)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        m = self.get_object()
        return Response(MovementSerializer(m.movements.all()[:100], many=True).data)

from rest_framework import serializers

from catalog.models import Category
from catalog.serializers import CategorySerializer, ImageSerializer

from .models import Material, SupplierProfile


class SupplierCardSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, default=None)

    class Meta:
        model = SupplierProfile
        fields = [
            "id", "name", "city_name", "area_name", "pickup_available", "delivery_available",
            "delivery_cost", "delivery_days", "logo",
        ]


class SupplierPublicSerializer(SupplierCardSerializer):
    public_phone = serializers.SerializerMethodField()
    materials_count = serializers.SerializerMethodField()

    class Meta(SupplierCardSerializer.Meta):
        fields = SupplierCardSerializer.Meta.fields + ["description", "public_phone", "materials_count", "created_at"]

    def get_public_phone(self, obj):
        return obj.public_phone if obj.contact_consent else None

    def get_materials_count(self, obj):
        return obj.materials.filter(is_deleted=False).count()


class SupplierOwnerSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = SupplierProfile
        fields = [
            "id", "name", "description", "city", "city_name", "area", "public_phone", "contact_consent",
            "pickup_available", "delivery_available", "delivery_cost", "delivery_days", "status", "logo",
            "created_at",
        ]
        read_only_fields = ["status", "logo", "created_at"]

    def validate(self, attrs):
        city = attrs.get("city") or getattr(self.instance, "city", None)
        area = attrs.get("area")
        if area and city and area.city_id != city.pk:
            raise serializers.ValidationError({"area": "المنطقة لا تتبع المدينة المختارة."})
        pickup = attrs.get("pickup_available", getattr(self.instance, "pickup_available", True))
        delivery = attrs.get("delivery_available", getattr(self.instance, "delivery_available", False))
        if not pickup and not delivery:
            raise serializers.ValidationError("اختر طريقة استلام واحدة على الأقل.")
        return attrs


class MaterialPublicSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    supplier = SupplierCardSerializer(read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Material
        fields = [
            "id", "title", "description", "specifications", "category", "unit", "unit_display", "price",
            "available_quantity", "min_order_quantity", "preparation_days", "is_available", "images",
            "supplier", "created_at",
        ]


class MaterialOwnerSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    initial_stock = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, min_value=0)

    class Meta:
        model = Material
        fields = [
            "id", "title", "description", "specifications", "category", "category_name", "unit", "unit_display",
            "price", "stock_quantity", "reserved_quantity", "available_quantity", "min_order_quantity",
            "preparation_days", "low_stock_threshold", "is_available", "initial_stock", "images",
            "created_at", "updated_at",
        ]
        read_only_fields = ["stock_quantity", "reserved_quantity", "created_at", "updated_at"]

    def validate_category(self, value):
        if value.kind != Category.Kind.MATERIAL or not value.is_active:
            raise serializers.ValidationError("اختر تصنيفًا صالحًا للمواد الخام.")
        return value

    def validate_unit(self, value):
        if self.instance and value != self.instance.unit and self.instance.reserved_quantity > 0:
            raise serializers.ValidationError("لا يمكن تغيير الوحدة وعليها كميات محجوزة.")
        return value

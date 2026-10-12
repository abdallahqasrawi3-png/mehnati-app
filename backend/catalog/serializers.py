from rest_framework import serializers

from core.validators import validate_image_file

from .models import BusinessImage, BusinessProfile, Category, Offer, OfferImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "kind", "icon", "sort_order", "is_active"]


class ImageSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    image = serializers.ImageField(read_only=True)


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField(validators=[validate_image_file])


class BusinessCardSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, default=None)

    class Meta:
        model = BusinessProfile
        fields = [
            "id", "name", "city_name", "area_name", "rating_avg", "rating_count",
            "pickup_available", "delivery_available", "logo",
        ]


class BusinessPublicSerializer(serializers.ModelSerializer):
    """Public view: general location only; contact details only with consent."""

    category = CategorySerializer(read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, default=None)
    work_images = ImageSerializer(many=True, read_only=True)
    public_phone = serializers.SerializerMethodField()
    public_whatsapp = serializers.SerializerMethodField()
    offers_count = serializers.SerializerMethodField()

    class Meta:
        model = BusinessProfile
        fields = [
            "id", "name", "description", "category", "city_name", "area_name", "public_phone", "public_whatsapp",
            "working_hours", "pickup_available", "delivery_available", "status", "rating_avg", "rating_count",
            "logo", "work_images", "offers_count", "created_at",
        ]

    def get_public_phone(self, obj):
        return obj.public_phone if obj.contact_consent else None

    def get_public_whatsapp(self, obj):
        return obj.public_whatsapp if obj.contact_consent else None

    def get_offers_count(self, obj):
        return obj.offers.filter(is_deleted=False).count()


class BusinessOwnerSerializer(serializers.ModelSerializer):
    work_images = ImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = BusinessProfile
        fields = [
            "id", "name", "description", "category", "category_name", "city", "city_name", "area",
            "public_phone", "public_whatsapp", "contact_consent", "working_hours", "pickup_available",
            "delivery_available", "status", "rating_avg", "rating_count", "logo", "work_images", "created_at",
        ]
        read_only_fields = ["status", "rating_avg", "rating_count", "logo", "created_at"]

    def validate_category(self, value):
        if value.kind != Category.Kind.OFFER or not value.is_active:
            raise serializers.ValidationError("اختر تصنيف نشاط صالحًا.")
        return value

    def validate(self, attrs):
        city = attrs.get("city") or getattr(self.instance, "city", None)
        area = attrs.get("area")
        if area and city and area.city_id != city.pk:
            raise serializers.ValidationError({"area": "المنطقة لا تتبع المدينة المختارة."})
        pickup = attrs.get("pickup_available", getattr(self.instance, "pickup_available", True))
        delivery = attrs.get("delivery_available", getattr(self.instance, "delivery_available", False))
        if not pickup and not delivery:
            raise serializers.ValidationError("اختر طريقة استلام واحدة على الأقل (استلام أو توصيل).")
        return attrs


class OfferPublicSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    business = BusinessCardSerializer(read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    offer_type_display = serializers.CharField(source="get_offer_type_display", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_orderable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id", "title", "description", "category", "offer_type", "offer_type_display", "price", "price_unit",
            "preparation_days", "service_duration", "is_available", "available_quantity", "is_orderable",
            "images", "business", "created_at",
        ]


class OfferOwnerSerializer(serializers.ModelSerializer):
    images = ImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    offer_type_display = serializers.CharField(source="get_offer_type_display", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    initial_stock = serializers.IntegerField(write_only=True, required=False, min_value=0)

    class Meta:
        model = Offer
        fields = [
            "id", "title", "description", "category", "category_name", "offer_type", "offer_type_display",
            "price", "price_unit", "unit_cost", "preparation_days", "service_duration", "is_available",
            "stock_quantity", "reserved_quantity", "available_quantity", "low_stock_threshold", "initial_stock",
            "images", "created_at", "updated_at",
        ]
        read_only_fields = ["stock_quantity", "reserved_quantity", "created_at", "updated_at"]

    def validate_category(self, value):
        if value.kind != Category.Kind.OFFER or not value.is_active:
            raise serializers.ValidationError("اختر تصنيفًا صالحًا للمنتجات والخدمات.")
        return value

    def validate_offer_type(self, value):
        if self.instance and value != self.instance.offer_type and self.instance.reserved_quantity > 0:
            raise serializers.ValidationError("لا يمكن تغيير نوع العرض وعليه كميات محجوزة لطلبات.")
        return value

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("العنوان قصير جدًا.")
        return value

from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.models import Area, City

from .models import Address, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "password", "full_name", "phone", "city"]
        extra_kwargs = {"full_name": {"required": True}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("هذا البريد مسجّل مسبقًا.")
        return value

    def validate(self, attrs):
        user = User(email=attrs["email"], full_name=attrs.get("full_name", ""))
        try:
            validate_password(attrs["password"], user)
        except Exception as e:
            raise serializers.ValidationError({"password": list(getattr(e, "messages", [str(e)]))})
        return attrs

    def create(self, validated):
        password = validated.pop("password")
        return User.objects.create_user(password=password, **validated)


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {"no_active_account": "البريد أو كلمة المرور غير صحيحة، أو الحساب موقوف."}

    def validate(self, attrs):
        attrs[self.username_field] = (attrs.get(self.username_field) or "").strip().lower()
        return super().validate(attrs)


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)
    business_profile_id = serializers.SerializerMethodField()
    supplier_profile_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "phone", "city", "city_name", "roles", "is_staff",
            "business_profile_id", "supplier_profile_id", "date_joined",
        ]
        read_only_fields = ["id", "email", "roles", "is_staff", "date_joined"]

    def get_business_profile_id(self, obj):
        bp = getattr(obj, "business_profile", None)
        return bp.pk if bp else None

    def get_supplier_profile_id(self, obj):
        sp = getattr(obj, "supplier_profile", None)
        return sp.pk if sp else None


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "كلمة المرور الحالية غير صحيحة."})
        try:
            validate_password(attrs["new_password"], user)
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(getattr(e, "messages", [str(e)]))})
        return attrs


def map_url(lat, lng):
    if lat is None or lng is None:
        return None
    return f"https://www.google.com/maps?q={lat},{lng}"


class AddressSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, default=None)
    # Accept any float precision from GPS / map links; stored rounded to 6 decimals (~10 cm).
    latitude = serializers.FloatField(required=False, allow_null=True, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, allow_null=True, min_value=-180, max_value=180)
    full_text = serializers.CharField(read_only=True)
    map_url = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = [
            "id", "label", "recipient_name", "phone", "city", "city_name", "area", "area_name",
            "street", "building", "floor", "apartment", "landmark", "details",
            "latitude", "longitude", "full_text", "map_url",
        ]

    def get_map_url(self, obj):
        return map_url(obj.latitude, obj.longitude)

    def validate(self, attrs):
        area = attrs.get("area")
        city = attrs.get("city") or getattr(self.instance, "city", None)
        if area and city and area.city_id != city.pk:
            raise serializers.ValidationError({"area": "المنطقة لا تتبع المدينة المختارة."})

        def current(name):
            return attrs[name] if name in attrs else getattr(self.instance, name, None)

        text_fields = ("street", "landmark", "details")
        if not any((current(f) or "").strip() for f in text_fields):
            raise serializers.ValidationError({"street": "اكتب الشارع أو أقرب معلم أو تفاصيل تساعد على الوصول."})

        lat, lng = current("latitude"), current("longitude")
        if (lat is None) != (lng is None):
            raise serializers.ValidationError({"latitude": "حدد الموقع على الخريطة كاملًا (خط العرض وخط الطول) أو احذفه."})
        if lat is not None and lat == 0 and lng == 0:
            raise serializers.ValidationError({"latitude": "إحداثيات الموقع غير صحيحة."})
        for name in ("latitude", "longitude"):
            if attrs.get(name) is not None:
                attrs[name] = Decimal(str(attrs[name])).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return attrs


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ["id", "name"]


class CitySerializer(serializers.ModelSerializer):
    areas = AreaSerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "areas"]


class AdminUserSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "is_staff", "roles", "date_joined", "last_login"]
        read_only_fields = fields

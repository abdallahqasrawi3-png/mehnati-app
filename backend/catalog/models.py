from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from core.validators import validate_image_file


class Category(models.Model):
    class Kind(models.TextChoices):
        OFFER = "offer", "منتجات وخدمات"
        MATERIAL = "material", "مواد خام"

    name = models.CharField("الاسم", max_length=80)
    kind = models.CharField("النوع", max_length=20, choices=Kind.choices, default=Kind.OFFER)
    icon = models.CharField("أيقونة", max_length=40, blank=True, help_text="اسم أيقونة اختياري للتطبيق")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("name", "kind")]
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"

    def __str__(self):
        return self.name


class ProfileStatus(models.TextChoices):
    ACTIVE = "active", "فعّال"
    SUSPENDED = "suspended", "موقوف"


class BusinessProfile(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_profile")
    name = models.CharField("اسم المشروع", max_length=120)
    description = models.TextField("وصف مختصر", max_length=2000, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="تصنيف النشاط")
    city = models.ForeignKey("core.City", on_delete=models.PROTECT, verbose_name="المدينة")
    area = models.ForeignKey("core.Area", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="المنطقة")
    # Contact details the owner explicitly agreed to publish
    public_phone = models.CharField("هاتف للنشر", max_length=30, blank=True)
    public_whatsapp = models.CharField("واتساب للنشر", max_length=30, blank=True)
    contact_consent = models.BooleanField("موافقة على نشر وسائل التواصل", default=False)
    working_hours = models.CharField("ساعات العمل", max_length=200, blank=True)
    pickup_available = models.BooleanField("استلام من المكان", default=True)
    delivery_available = models.BooleanField("توصيل", default=False)
    status = models.CharField("حالة الحساب", max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    rating_avg = models.DecimalField("متوسط التقييم", max_digits=3, decimal_places=2, default=Decimal("0"))
    rating_count = models.PositiveIntegerField("عدد التقييمات", default=0)
    logo = models.ImageField("الشعار", upload_to="business/logos/", blank=True, validators=[validate_image_file])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "مشروع منزلي"
        verbose_name_plural = "المشاريع المنزلية"

    def __str__(self):
        return self.name


class BusinessImage(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="work_images")
    image = models.ImageField(upload_to="business/work/", validators=[validate_image_file])
    caption = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "صورة عمل"
        verbose_name_plural = "صور الأعمال"


class Offer(models.Model):
    class OfferType(models.TextChoices):
        READY = "ready", "منتج جاهز بكمية"
        MADE_TO_ORDER = "made_to_order", "منتج حسب الطلب"
        SERVICE = "service", "خدمة"

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="offers")
    title = models.CharField("العنوان", max_length=150)
    description = models.TextField("الوصف", max_length=4000, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="التصنيف")
    offer_type = models.CharField("نوع العرض", max_length=20, choices=OfferType.choices, default=OfferType.READY)
    price = models.DecimalField(
        "السعر", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    price_unit = models.CharField("وحدة السعر", max_length=40, default="للقطعة")
    unit_cost = models.DecimalField(
        "تكلفة الوحدة (خاصة)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="تُستخدم في التقارير فقط ولا تظهر للعملاء",
    )
    preparation_days = models.PositiveIntegerField("مدة التجهيز (أيام)", default=0)
    service_duration = models.CharField("مدة تنفيذ الخدمة", max_length=60, blank=True)
    is_available = models.BooleanField("متاح", default=True)
    # Stock applies only to ready-made products
    stock_quantity = models.PositiveIntegerField("الكمية في المخزون", default=0)
    reserved_quantity = models.PositiveIntegerField("الكمية المحجوزة", default=0)
    low_stock_threshold = models.PositiveIntegerField("حد التنبيه", default=0)
    is_deleted = models.BooleanField("محذوف", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "عرض"
        verbose_name_plural = "العروض (منتجات وخدمات)"
        constraints = [
            models.CheckConstraint(
                condition=Q(reserved_quantity__lte=F("stock_quantity")), name="offer_reserved_lte_stock"
            ),
        ]
        indexes = [
            models.Index(fields=["is_deleted", "is_available"]),
            models.Index(fields=["price"]),
            models.Index(fields=["offer_type"]),
        ]

    def __str__(self):
        return self.title

    @property
    def tracks_stock(self):
        return self.offer_type == self.OfferType.READY

    @property
    def available_quantity(self):
        if not self.tracks_stock:
            return None
        return self.stock_quantity - self.reserved_quantity

    @property
    def is_orderable(self):
        if self.is_deleted or not self.is_available or self.business.status != ProfileStatus.ACTIVE:
            return False
        if self.tracks_stock:
            return self.available_quantity > 0
        return True


class OfferImage(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="offers/", validators=[validate_image_file])
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "صورة عرض"
        verbose_name_plural = "صور العروض"

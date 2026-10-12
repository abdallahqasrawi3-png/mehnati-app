from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from catalog.models import Category, ProfileStatus
from core.validators import validate_image_file


class SupplierProfile(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="supplier_profile")
    name = models.CharField("الاسم التجاري", max_length=120)
    description = models.TextField("الوصف", max_length=2000, blank=True)
    city = models.ForeignKey("core.City", on_delete=models.PROTECT, verbose_name="المدينة")
    area = models.ForeignKey("core.Area", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="المنطقة")
    public_phone = models.CharField("هاتف للنشر", max_length=30, blank=True)
    contact_consent = models.BooleanField("موافقة على نشر الهاتف", default=False)
    pickup_available = models.BooleanField("استلام من المورد", default=True)
    delivery_available = models.BooleanField("توصيل", default=False)
    delivery_cost = models.DecimalField(
        "تكلفة التوصيل التقديرية", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    delivery_days = models.PositiveIntegerField("مدة التوصيل المتوقعة (أيام)", null=True, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=ProfileStatus.choices, default=ProfileStatus.ACTIVE)
    logo = models.ImageField("الشعار", upload_to="suppliers/logos/", blank=True, validators=[validate_image_file])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "مورد"
        verbose_name_plural = "الموردون"

    def __str__(self):
        return self.name


class Material(models.Model):
    class Unit(models.TextChoices):
        PIECE = "piece", "قطعة"
        METER = "meter", "متر"
        KG = "kg", "كيلوغرام"
        GRAM = "gram", "غرام"
        PACK = "pack", "عبوة"
        ROLL = "roll", "لفة"
        LITER = "liter", "لتر"
        BOX = "box", "صندوق"

    supplier = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField("الاسم", max_length=150)
    description = models.TextField("الوصف", max_length=4000, blank=True)
    specifications = models.TextField("المواصفات", max_length=2000, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="التصنيف")
    unit = models.CharField("وحدة القياس", max_length=10, choices=Unit.choices, default=Unit.PIECE)
    price = models.DecimalField(
        "سعر الوحدة", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    stock_quantity = models.DecimalField(
        "الكمية المتاحة", max_digits=12, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    reserved_quantity = models.DecimalField("الكمية المحجوزة", max_digits=12, decimal_places=2, default=Decimal("0"))
    min_order_quantity = models.DecimalField(
        "الحد الأدنى للشراء", max_digits=12, decimal_places=2, default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    preparation_days = models.PositiveIntegerField("مدة التجهيز (أيام)", default=0)
    low_stock_threshold = models.DecimalField(
        "حد التنبيه", max_digits=12, decimal_places=2, default=Decimal("0")
    )
    is_available = models.BooleanField("متاح", default=True)
    is_deleted = models.BooleanField("محذوف", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "مادة خام"
        verbose_name_plural = "المواد الخام"
        constraints = [
            models.CheckConstraint(condition=Q(stock_quantity__gte=0), name="material_stock_non_negative"),
            models.CheckConstraint(condition=Q(reserved_quantity__gte=0), name="material_reserved_non_negative"),
            models.CheckConstraint(
                condition=Q(reserved_quantity__lte=F("stock_quantity")), name="material_reserved_lte_stock"
            ),
        ]
        indexes = [models.Index(fields=["is_deleted", "is_available"]), models.Index(fields=["price"])]

    def __str__(self):
        return self.title

    @property
    def available_quantity(self):
        return self.stock_quantity - self.reserved_quantity


class MaterialImage(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="materials/", validators=[validate_image_file])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "صورة مادة"
        verbose_name_plural = "صور المواد"

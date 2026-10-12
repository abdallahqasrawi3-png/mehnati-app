from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Carrier(models.Model):
    """A delivery company. `integration` selects an adapter in shipping.carriers."""

    name = models.CharField("اسم شركة التوصيل", max_length=120, unique=True)
    integration = models.CharField(
        "نوع التكامل", max_length=30, default="manual",
        help_text="manual = إدخال يدوي بدون API. أي قيمة أخرى يجب أن تطابق مكوّن تكامل مسجل.",
    )
    phone = models.CharField("هاتف", max_length=30, blank=True)
    is_active = models.BooleanField("فعالة", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "شركة توصيل"
        verbose_name_plural = "شركات التوصيل"

    def __str__(self):
        return self.name


class Shipment(models.Model):
    class Kind(models.TextChoices):
        SALES = "sales", "من صاحب المشروع إلى العميل"
        PURCHASE = "purchase", "من المورد إلى صاحب المشروع"

    class Status(models.TextChoices):
        CREATED = "created", "تم التسجيل"
        PENDING_CARRIER = "pending_carrier", "بانتظار تأكيد شركة التوصيل"
        PICKED_UP = "picked_up", "استلمتها شركة التوصيل"
        IN_TRANSIT = "in_transit", "في الطريق"
        DELIVERED = "delivered", "تم التسليم"
        FAILED = "failed", "تعذر التسليم"
        RETURNED = "returned", "مرتجعة"

    kind = models.CharField("نوع الشحنة", max_length=10, choices=Kind.choices)
    sales_order = models.OneToOneField(
        "orders.SalesOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="shipment"
    )
    purchase_order = models.OneToOneField(
        "orders.PurchaseOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="shipment"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    carrier = models.ForeignKey(Carrier, null=True, blank=True, on_delete=models.PROTECT)
    carrier_name = models.CharField("اسم شركة التوصيل (يدوي)", max_length=120, blank=True)
    tracking_number = models.CharField("رقم التتبع", max_length=80, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.CREATED)
    cost = models.DecimalField(
        "التكلفة", max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))]
    )
    cost_is_final = models.BooleanField("التكلفة نهائية", default=False)
    estimated_arrival = models.DateField("الوصول المتوقع", null=True, blank=True)
    # External integration bookkeeping
    idempotency_key = models.CharField(max_length=64, unique=True)
    external_reference = models.CharField(max_length=120, blank=True)
    external_confirmed = models.BooleanField("مؤكدة من شركة التوصيل", default=False)
    last_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField("آخر تحديث", auto_now=True)

    class Meta:
        ordering = ["-last_update"]
        verbose_name = "شحنة"
        verbose_name_plural = "الشحنات"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind="sales", sales_order__isnull=False, purchase_order__isnull=True)
                    | Q(kind="purchase", sales_order__isnull=True, purchase_order__isnull=False)
                ),
                name="shipment_matches_kind",
            )
        ]

    def __str__(self):
        return f"شحنة #{self.pk}"

    @property
    def order(self):
        return self.sales_order if self.kind == self.Kind.SALES else self.purchase_order

    @property
    def display_carrier(self):
        return self.carrier.name if self.carrier else self.carrier_name


class ShipmentEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20, choices=Shipment.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=20, default="manual")  # manual | carrier
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

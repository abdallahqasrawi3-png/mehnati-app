from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Fulfillment(models.TextChoices):
    PICKUP = "pickup", "استلام من البائع"
    DELIVERY = "delivery", "توصيل"


class DeliveryPayer(models.TextChoices):
    BUYER = "buyer", "المشتري"
    SELLER = "seller", "البائع"


class DeliverySnapshot(models.Model):
    """Private delivery details copied when the order is created."""

    fulfillment = models.CharField("طريقة الاستلام", max_length=10, choices=Fulfillment.choices, default=Fulfillment.PICKUP)
    recipient_name = models.CharField("اسم المستلم", max_length=120, blank=True)
    recipient_phone = models.CharField("هاتف المستلم", max_length=30, blank=True)
    delivery_city = models.CharField("المدينة", max_length=80, blank=True)
    delivery_area = models.CharField("المنطقة", max_length=80, blank=True)
    delivery_address = models.CharField("العنوان", max_length=500, blank=True)
    delivery_landmark = models.CharField("أقرب معلم", max_length=120, blank=True)
    delivery_latitude = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_fee = models.DecimalField(
        "تكلفة التوصيل", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    delivery_payer = models.CharField("من يدفع التوصيل", max_length=10, choices=DeliveryPayer.choices, default=DeliveryPayer.BUYER)
    delivery_fee_is_final = models.BooleanField("التكلفة نهائية", default=False)

    class Meta:
        abstract = True


class SalesOrder(DeliverySnapshot):
    class Status(models.TextChoices):
        PENDING = "pending", "بانتظار قبول صاحب المشروع"
        ACCEPTED = "accepted", "مقبول"
        PREPARING = "preparing", "قيد التجهيز"
        READY = "ready", "جاهز للاستلام أو الشحن"
        IN_TRANSIT = "in_transit", "في الطريق"
        COMPLETED = "completed", "مكتمل"
        REJECTED = "rejected", "مرفوض"
        CANCELLED = "cancelled", "ملغى"
        DELIVERY_FAILED = "delivery_failed", "تعذّر التسليم"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_orders")
    business = models.ForeignKey("catalog.BusinessProfile", on_delete=models.PROTECT, related_name="sales_orders")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    notes = models.TextField("ملاحظات العميل", max_length=1000, blank=True)
    requested_date = models.DateField("الموعد المطلوب (للخدمات)", null=True, blank=True)
    subtotal = models.DecimalField("مجموع العناصر", max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب بيع"
        verbose_name_plural = "طلبات البيع"

    def __str__(self):
        return f"طلب بيع #{self.pk}"

    @property
    def total(self):
        fee = self.delivery_fee or Decimal("0")
        return self.subtotal + (fee if self.delivery_payer == DeliveryPayer.BUYER else Decimal("0"))


class SalesOrderItem(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="items")
    offer = models.ForeignKey("catalog.Offer", null=True, on_delete=models.SET_NULL, related_name="order_items")
    # Snapshots taken when the order is created
    title = models.CharField(max_length=150)
    offer_type = models.CharField(max_length=20)
    price_unit = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    stock_reserved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "عنصر طلب بيع"
        verbose_name_plural = "عناصر طلبات البيع"


class PurchaseOrder(DeliverySnapshot):
    class Status(models.TextChoices):
        PENDING = "pending", "بانتظار قبول المورد"
        ACCEPTED = "accepted", "مقبول"
        PREPARING = "preparing", "قيد التجهيز"
        SHIPPED = "shipped", "مشحون / جاهز للاستلام"
        RECEIVED = "received", "مستلم"
        REJECTED = "rejected", "مرفوض"
        CANCELLED = "cancelled", "ملغى"

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_orders")
    business = models.ForeignKey("catalog.BusinessProfile", on_delete=models.PROTECT, related_name="purchase_orders")
    supplier = models.ForeignKey("suppliers.SupplierProfile", on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    notes = models.TextField("ملاحظات", max_length=1000, blank=True)
    subtotal = models.DecimalField("مجموع العناصر", max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب شراء مواد خام"
        verbose_name_plural = "طلبات شراء المواد الخام"

    def __str__(self):
        return f"طلب شراء #{self.pk}"

    @property
    def total(self):
        fee = self.delivery_fee or Decimal("0")
        return self.subtotal + (fee if self.delivery_payer == DeliveryPayer.BUYER else Decimal("0"))


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey("suppliers.Material", null=True, on_delete=models.SET_NULL, related_name="order_items")
    title = models.CharField(max_length=150)
    unit = models.CharField(max_length=10)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    stock_reserved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "عنصر طلب شراء"
        verbose_name_plural = "عناصر طلبات الشراء"


class OrderStatusLog(models.Model):
    sales_order = models.ForeignKey(SalesOrder, null=True, blank=True, on_delete=models.CASCADE, related_name="status_logs")
    purchase_order = models.ForeignKey(
        PurchaseOrder, null=True, blank=True, on_delete=models.CASCADE, related_name="status_logs"
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(sales_order__isnull=False, purchase_order__isnull=True)
                    | Q(sales_order__isnull=True, purchase_order__isnull=False)
                ),
                name="statuslog_exactly_one_order",
            )
        ]

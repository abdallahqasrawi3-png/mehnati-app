from django.conf import settings
from django.db import models
from django.db.models import Q


class InventoryMovement(models.Model):
    class Kind(models.TextChoices):
        ADD = "add", "إضافة كمية"
        REMOVE = "remove", "خصم يدوي"
        RESERVE = "reserve", "حجز لطلب"
        RELEASE = "release", "تحرير حجز (رفض/إلغاء)"
        SALE = "sale", "إكمال بيع"

    offer = models.ForeignKey("catalog.Offer", null=True, blank=True, on_delete=models.CASCADE, related_name="movements")
    material = models.ForeignKey(
        "suppliers.Material", null=True, blank=True, on_delete=models.CASCADE, related_name="movements"
    )
    kind = models.CharField("نوع الحركة", max_length=10, choices=Kind.choices)
    quantity = models.DecimalField("الكمية", max_digits=12, decimal_places=2)
    stock_after = models.DecimalField("المخزون بعد الحركة", max_digits=12, decimal_places=2)
    reserved_after = models.DecimalField("المحجوز بعد الحركة", max_digits=12, decimal_places=2)
    sales_order = models.ForeignKey("orders.SalesOrder", null=True, blank=True, on_delete=models.SET_NULL)
    purchase_order = models.ForeignKey("orders.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField("ملاحظة", max_length=255, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"
        constraints = [
            models.CheckConstraint(
                condition=(Q(offer__isnull=False, material__isnull=True) | Q(offer__isnull=True, material__isnull=False)),
                name="movement_exactly_one_item",
            )
        ]

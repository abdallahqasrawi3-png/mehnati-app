from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        NEW_ORDER = "new_order", "طلب جديد"
        ORDER_STATUS = "order_status", "تغير حالة طلب"
        LOW_STOCK = "low_stock", "انخفاض المخزون"
        SHIPMENT = "shipment", "تحديث شحنة"
        REVIEW = "review", "تقييم جديد"
        SYSTEM = "system", "إشعار"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=500, blank=True)
    ref_type = models.CharField(max_length=30, blank=True)
    ref_id = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"

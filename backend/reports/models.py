from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):
    """Direct expenses recorded by a home-business owner (used in profit estimate)."""

    class Category(models.TextChoices):
        PACKAGING = "packaging", "تغليف"
        DELIVERY = "delivery", "توصيل على حساب المشروع"
        COMMISSION = "commission", "عمولات"
        MATERIALS_USED = "materials_used", "مواد مستهلكة"
        OTHER = "other", "أخرى"

    business = models.ForeignKey("catalog.BusinessProfile", on_delete=models.CASCADE, related_name="expenses")
    date = models.DateField("التاريخ")
    category = models.CharField("النوع", max_length=20, choices=Category.choices, default=Category.OTHER)
    amount = models.DecimalField(
        "المبلغ", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    note = models.CharField("ملاحظة", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "مصروف"
        verbose_name_plural = "المصاريف"

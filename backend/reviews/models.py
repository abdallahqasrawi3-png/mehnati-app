from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count


class Review(models.Model):
    """One review per completed sales order (rates the overall experience 1-5)."""

    order = models.OneToOneField("orders.SalesOrder", on_delete=models.CASCADE, related_name="review")
    business = models.ForeignKey("catalog.BusinessProfile", on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField("التقييم", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("التعليق", max_length=1000, blank=True)
    is_hidden = models.BooleanField("مخفي من الإدارة", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_1_5")
        ]

    def __str__(self):
        return f"{self.rating}★ - {self.business}"


def refresh_business_rating(business):
    agg = Review.objects.filter(business=business, is_hidden=False).aggregate(avg=Avg("rating"), n=Count("id"))
    business.rating_avg = round(agg["avg"] or 0, 2)
    business.rating_count = agg["n"] or 0
    business.save(update_fields=["rating_avg", "rating_count"])

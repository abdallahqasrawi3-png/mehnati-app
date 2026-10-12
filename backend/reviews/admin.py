from django.contrib import admin

from .models import Review, refresh_business_rating


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "business", "customer", "rating", "is_hidden", "created_at"]
    list_filter = ["rating", "is_hidden"]
    readonly_fields = ["order", "business", "customer", "rating", "comment", "created_at"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        refresh_business_rating(obj.business)

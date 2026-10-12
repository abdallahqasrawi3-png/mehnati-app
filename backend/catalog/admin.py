from django.contrib import admin

from .models import BusinessImage, BusinessProfile, Category, Offer, OfferImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "sort_order", "is_active"]
    list_filter = ["kind", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["name"]


class BusinessImageInline(admin.TabularInline):
    model = BusinessImage
    extra = 0


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "category", "city", "status", "rating_avg", "rating_count"]
    list_filter = ["status", "category", "city"]
    search_fields = ["name", "owner__email"]
    readonly_fields = ["rating_avg", "rating_count"]
    inlines = [BusinessImageInline]


class OfferImageInline(admin.TabularInline):
    model = OfferImage
    extra = 0


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ["title", "business", "offer_type", "price", "stock_quantity", "reserved_quantity", "is_available", "is_deleted"]
    list_filter = ["offer_type", "is_available", "is_deleted", "category"]
    search_fields = ["title", "business__name"]
    readonly_fields = ["stock_quantity", "reserved_quantity"]
    inlines = [OfferImageInline]

from django.contrib import admin

from .models import Material, MaterialImage, SupplierProfile


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "city", "status", "delivery_available"]
    list_filter = ["status", "city"]
    search_fields = ["name", "owner__email"]


class MaterialImageInline(admin.TabularInline):
    model = MaterialImage
    extra = 0


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["title", "supplier", "unit", "price", "stock_quantity", "reserved_quantity", "is_available", "is_deleted"]
    list_filter = ["unit", "is_available", "is_deleted", "category"]
    search_fields = ["title", "supplier__name"]
    readonly_fields = ["stock_quantity", "reserved_quantity"]
    inlines = [MaterialImageInline]

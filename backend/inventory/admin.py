from django.contrib import admin

from .models import InventoryMovement


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ["created_at", "kind", "offer", "material", "quantity", "stock_after", "reserved_after"]
    list_filter = ["kind"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

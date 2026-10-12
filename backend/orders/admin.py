from django.contrib import admin

from .models import OrderStatusLog, PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class SalesItemInline(ReadOnlyInline):
    model = SalesOrderItem


class PurchaseItemInline(ReadOnlyInline):
    model = PurchaseOrderItem


class SalesLogInline(ReadOnlyInline):
    model = OrderStatusLog
    fk_name = "sales_order"
    exclude = ["purchase_order"]


class PurchaseLogInline(ReadOnlyInline):
    model = OrderStatusLog
    fk_name = "purchase_order"
    exclude = ["sales_order"]


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    """Orders change status only through the app's rules, so admin is read-only."""

    list_display = ["id", "customer", "business", "status", "subtotal", "created_at"]
    list_filter = ["status", "fulfillment"]
    search_fields = ["id", "customer__email", "business__name"]
    inlines = [SalesItemInline, SalesLogInline]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "business", "supplier", "status", "subtotal", "created_at"]
    list_filter = ["status", "fulfillment"]
    inlines = [PurchaseItemInline, PurchaseLogInline]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

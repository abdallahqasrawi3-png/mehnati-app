from django.contrib import admin

from .models import Carrier, Shipment, ShipmentEvent


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ["name", "integration", "phone", "is_active"]


class EventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    can_delete = False


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ["id", "kind", "display_carrier", "tracking_number", "status", "external_confirmed", "last_update"]
    list_filter = ["kind", "status", "external_confirmed"]
    inlines = [EventInline]

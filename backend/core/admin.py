from django.contrib import admin

from .models import AbuseReport, Area, AuditLog, City, ContactMessage


class AreaInline(admin.TabularInline):
    model = Area
    extra = 1


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    inlines = [AreaInline]
    search_fields = ["name"]


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = ["id", "target_type", "target_id", "reporter", "status", "created_at"]
    list_filter = ["status", "target_type"]
    readonly_fields = ["reporter", "target_type", "target_id", "reason", "created_at"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "target_type", "target_id"]
    list_filter = ["action"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "kind", "name", "phone", "status", "created_at"]
    list_filter = ["status", "kind"]
    search_fields = ["name", "phone", "message", "order_ref"]
    readonly_fields = ["user", "name", "phone", "kind", "order_ref", "message", "created_at"]

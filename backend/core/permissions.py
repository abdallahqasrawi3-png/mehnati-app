from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    message = "هذه العملية مخصصة لإدارة المنصة."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class HasBusinessProfile(BasePermission):
    message = "يجب إنشاء ملف مشروع منزلي فعّال أولًا."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        bp = getattr(u, "business_profile", None)
        return bp is not None and bp.status == "active"


class HasSupplierProfile(BasePermission):
    message = "يجب إنشاء ملف مورد فعّال أولًا."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        sp = getattr(u, "supplier_profile", None)
        return sp is not None and sp.status == "active"

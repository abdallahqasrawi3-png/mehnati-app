from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.static import serve
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts import views as acc
from ai_assistant import views as ai
from catalog import views as cat
from core import views as core
from inventory import views as inv
from notifications.views import NotificationViewSet
from orders.views import PurchaseOrderViewSet, SalesOrderViewSet
from reports import views as rep
from reviews.views import ReviewViewSet
from shipping.views import CarrierViewSet, ShipmentViewSet
from suppliers import views as sup

admin.site.site_header = "إدارة منصة مهنتي"
admin.site.site_title = "مهنتي"
admin.site.index_title = "لوحة الإدارة"

router = DefaultRouter()
router.register("addresses", acc.AddressViewSet, basename="address")
router.register("categories", cat.CategoryViewSet, basename="category")
router.register("offers", cat.OfferViewSet, basename="offer")
router.register("businesses", cat.BusinessViewSet, basename="business")
router.register("my/offers", cat.MyOfferViewSet, basename="my-offer")
router.register("suppliers", sup.SupplierViewSet, basename="supplier")
router.register("materials", sup.MaterialViewSet, basename="material")
router.register("my/materials", sup.MyMaterialViewSet, basename="my-material")
router.register("sales-orders", SalesOrderViewSet, basename="sales-order")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("carriers", CarrierViewSet, basename="carrier")
router.register("shipments", ShipmentViewSet, basename="shipment")
router.register("reviews", ReviewViewSet, basename="review")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("expenses", rep.ExpenseViewSet, basename="expense")
router.register("abuse-reports", core.AbuseReportViewSet, basename="abuse-report")
router.register("admin/users", acc.AdminUserViewSet, basename="admin-user")
router.register("admin/abuse-reports", core.AdminAbuseReportViewSet, basename="admin-abuse-report")
router.register("admin/profiles", core.AdminProfileStatusViewSet, basename="admin-profile")


def health(request):
    return JsonResponse({"status": "ok"})


api = [
    path("health/", health),
    path("auth/register/", acc.RegisterView.as_view()),
    path("auth/login/", acc.LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/logout/", acc.LogoutView.as_view()),
    path("auth/me/", acc.MeView.as_view()),
    path("auth/change-password/", acc.ChangePasswordView.as_view()),
    path("cities/", acc.CityListView.as_view()),
    path("my/business/", cat.MyBusinessView.as_view()),
    path("my/business/logo/", cat.MyBusinessLogoView.as_view()),
    path("my/business/images/", cat.MyBusinessImagesView.as_view()),
    path("my/business/images/<int:image_id>/", cat.MyBusinessImagesView.as_view()),
    path("my/supplier/", sup.MySupplierView.as_view()),
    path("inventory/low-stock/", inv.LowStockView.as_view()),
    path("reports/business/", rep.BusinessReportView.as_view()),
    path("reports/supplier/", rep.SupplierReportView.as_view()),
    path("reports/admin/", rep.AdminIndicatorsView.as_view()),
    path("ai/status/", ai.AIStatusView.as_view()),
    path("ai/search/", ai.SmartSearchView.as_view()),
    path("ai/marketing-draft/", ai.MarketingDraftView.as_view()),
    path("ai/business-summary/", ai.BusinessSummaryView.as_view()),
    path("", include(router.urls)),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api)),
]

if settings.DEBUG:
    # Development only; in production serve /media from the web server (never executed).
    urlpatterns += [path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT})]

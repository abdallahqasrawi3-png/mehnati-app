from django.db.models import F
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Offer
from suppliers.models import Material


class LowStockView(APIView):
    """Items of the signed-in owner/supplier whose available quantity is at or below the alert threshold."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        result = {"offers": [], "materials": []}
        bp = getattr(request.user, "business_profile", None)
        if bp:
            qs = Offer.objects.filter(
                business=bp, is_deleted=False, offer_type=Offer.OfferType.READY, low_stock_threshold__gt=0,
                stock_quantity__lte=F("reserved_quantity") + F("low_stock_threshold"),
            )
            result["offers"] = [
                {"id": o.pk, "title": o.title, "available": o.available_quantity, "threshold": o.low_stock_threshold}
                for o in qs
            ]
        sp = getattr(request.user, "supplier_profile", None)
        if sp:
            qs = Material.objects.filter(
                supplier=sp, is_deleted=False, low_stock_threshold__gt=0,
                stock_quantity__lte=F("reserved_quantity") + F("low_stock_threshold"),
            )
            result["materials"] = [
                {"id": m.pk, "title": m.title, "available": m.available_quantity, "threshold": m.low_stock_threshold,
                 "unit": m.get_unit_display()}
                for m in qs
            ]
        return Response(result)

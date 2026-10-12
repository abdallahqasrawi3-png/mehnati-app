from rest_framework import permissions, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasBusinessProfile, HasSupplierProfile, IsPlatformAdmin

from . import service
from .models import Expense


def _dates(request):
    p = request.query_params
    df, dt = p.get("from"), p.get("to")
    if df and dt:
        ser = serializers.DateField()
        return ser.to_internal_value(df), ser.to_internal_value(dt)
    return None, None


class BusinessReportView(APIView):
    permission_classes = [HasBusinessProfile]

    def get(self, request):
        df, dt = _dates(request)
        return Response(service.business_report(
            request.user.business_profile, request.query_params.get("period", "month"), df, dt
        ))


class SupplierReportView(APIView):
    permission_classes = [HasSupplierProfile]

    def get(self, request):
        df, dt = _dates(request)
        return Response(service.supplier_report(
            request.user.supplier_profile, request.query_params.get("period", "month"), df, dt
        ))


class AdminIndicatorsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        return Response(service.admin_indicators())


class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "date", "category", "category_display", "amount", "note", "created_at"]


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [HasBusinessProfile]

    def get_queryset(self):
        return Expense.objects.filter(business=self.request.user.business_profile)

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business_profile)

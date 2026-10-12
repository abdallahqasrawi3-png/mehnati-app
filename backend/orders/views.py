from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import service
from .models import PurchaseOrder, SalesOrder
from .serializers import (
    DeliveryTermsSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderSerializer,
    SalesOrderCreateSerializer,
    SalesOrderListSerializer,
    SalesOrderSerializer,
    TransitionSerializer,
)


class SalesOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Only the customer and the business owner of an order can see it."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = SalesOrder.objects.filter(Q(customer=u) | Q(business__owner=u)).select_related(
            "business", "customer"
        ).prefetch_related("items", "status_logs__actor")
        role = self.request.query_params.get("role")
        if role == "customer":
            qs = qs.filter(customer=u)
        elif role == "business":
            qs = qs.filter(business__owner=u)
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status__in=st.split(","))
        return qs

    def get_serializer_class(self):
        return SalesOrderListSerializer if self.action == "list" else SalesOrderSerializer

    def create(self, request):
        ser = SalesOrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = service.create_sales_order(request.user, **ser.validated_data)
        order = self.get_queryset().get(pk=order.pk)
        return Response(SalesOrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        order = self.get_object()  # 404 if not a party to the order
        ser = TransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        service.transition_sales_order(request.user, order.pk, ser.validated_data["status"], ser.validated_data.get("note", ""))
        order = self.get_queryset().get(pk=order.pk)
        return Response(SalesOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def delivery(self, request, pk=None):
        order = self.get_object()
        ser = DeliveryTermsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        service.set_delivery_terms(request.user, order, **ser.validated_data)
        order = self.get_queryset().get(pk=order.pk)
        return Response(SalesOrderSerializer(order, context={"request": request}).data)


class PurchaseOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Only the purchasing business owner and the supplier can see a purchase order."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = PurchaseOrder.objects.filter(Q(buyer=u) | Q(supplier__owner=u)).select_related(
            "business", "supplier"
        ).prefetch_related("items", "status_logs__actor")
        role = self.request.query_params.get("role")
        if role == "buyer":
            qs = qs.filter(buyer=u)
        elif role == "supplier":
            qs = qs.filter(supplier__owner=u)
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status__in=st.split(","))
        return qs

    def get_serializer_class(self):
        return PurchaseOrderListSerializer if self.action == "list" else PurchaseOrderSerializer

    def create(self, request):
        ser = PurchaseOrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = service.create_purchase_order(request.user, **ser.validated_data)
        order = self.get_queryset().get(pk=order.pk)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        order = self.get_object()
        ser = TransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        service.transition_purchase_order(request.user, order.pk, ser.validated_data["status"], ser.validated_data.get("note", ""))
        order = self.get_queryset().get(pk=order.pk)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def delivery(self, request, pk=None):
        order = self.get_object()
        ser = DeliveryTermsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        service.set_delivery_terms(request.user, order, **ser.validated_data)
        order = self.get_queryset().get(pk=order.pk)
        return Response(PurchaseOrderSerializer(order, context={"request": request}).data)

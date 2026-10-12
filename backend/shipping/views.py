from django.db.models import Q
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.serializers import map_url

from . import service
from .models import Carrier, Shipment, ShipmentEvent


class CarrierSerializer(serializers.ModelSerializer):
    supports_api = serializers.SerializerMethodField()

    class Meta:
        model = Carrier
        fields = ["id", "name", "phone", "integration", "supports_api"]

    def get_supports_api(self, obj):
        return obj.integration != "manual"


class EventSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ShipmentEvent
        fields = ["status", "status_display", "note", "source", "created_at"]


class ShipmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    carrier_display = serializers.CharField(source="display_carrier", read_only=True)
    order_id = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)
    delivery_address = serializers.SerializerMethodField()
    events = EventSerializer(many=True, read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "id", "kind", "kind_display", "order_id", "sender_name", "recipient_name", "delivery_address",
            "carrier", "carrier_display", "tracking_number", "status", "status_display", "cost", "cost_is_final",
            "estimated_arrival", "external_confirmed", "last_error", "created_at", "last_update", "events", "my_role",
        ]

    def get_order_id(self, obj):
        return obj.sales_order_id or obj.purchase_order_id

    def get_my_role(self, obj):
        uid = self.context["request"].user.pk
        return "sender" if obj.sender_id == uid else "recipient"

    def get_delivery_address(self, obj):
        # Only parties of the shipment reach this serializer (queryset is restricted).
        o = obj.order
        return {
            "recipient_name": o.recipient_name, "phone": o.recipient_phone,
            "city": o.delivery_city, "area": o.delivery_area, "address": o.delivery_address,
            "landmark": o.delivery_landmark, "map_url": map_url(o.delivery_latitude, o.delivery_longitude),
        }


class ShipmentCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Shipment.Kind.choices)
    order_id = serializers.IntegerField()
    carrier_id = serializers.IntegerField(required=False, allow_null=True)
    carrier_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    tracking_number = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True)
    cost_is_final = serializers.BooleanField(required=False, default=False)
    estimated_arrival = serializers.DateField(required=False, allow_null=True)


class ShipmentUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Shipment.Status.choices)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    tracking_number = serializers.CharField(max_length=80, required=False, allow_blank=True)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True)
    cost_is_final = serializers.BooleanField(required=False)
    estimated_arrival = serializers.DateField(required=False, allow_null=True)


class CarrierViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CarrierSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    queryset = Carrier.objects.filter(is_active=True)


class ShipmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        return (
            Shipment.objects.filter(Q(sender=u) | Q(recipient=u))
            .select_related("carrier", "sender", "recipient", "sales_order", "purchase_order")
            .prefetch_related("events")
        )

    def create(self, request):
        ser = ShipmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        shipment, created = service.create_shipment(request.user, **ser.validated_data)
        shipment = self.get_queryset().get(pk=shipment.pk)
        return Response(
            self.get_serializer(shipment).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        shipment = self.get_object()
        ser = ShipmentUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        service.update_shipment(request.user, shipment, **ser.validated_data)
        return Response(self.get_serializer(self.get_queryset().get(pk=shipment.pk)).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        shipment = self.get_object()
        service.retry_external(request.user, shipment)
        return Response(self.get_serializer(self.get_queryset().get(pk=shipment.pk)).data)

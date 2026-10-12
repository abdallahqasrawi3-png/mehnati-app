from decimal import Decimal

from rest_framework import serializers

from accounts.serializers import map_url

from .models import DeliveryPayer, Fulfillment, OrderStatusLog, PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem
from .service import purchase_role, sales_role
from .workflow import NEXT_STEP_HINTS, allowed_next


class StatusLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)

    class Meta:
        model = OrderStatusLog
        fields = ["from_status", "to_status", "actor_name", "note", "created_at"]


class SalesItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderItem
        fields = ["id", "offer", "title", "offer_type", "price_unit", "unit_price", "quantity", "line_total"]


class PurchaseItemSerializer(serializers.ModelSerializer):
    unit_display = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "material", "title", "unit", "unit_display", "unit_price", "quantity", "line_total"]

    def get_unit_display(self, obj):
        from suppliers.models import Material

        try:
            return Material.Unit(obj.unit).label
        except ValueError:
            return obj.unit


DELIVERY_FIELDS = [
    "fulfillment", "recipient_name", "recipient_phone", "delivery_city", "delivery_area", "delivery_address",
    "delivery_landmark", "delivery_latitude", "delivery_longitude", "delivery_map_url",
    "delivery_fee", "delivery_payer", "delivery_fee_is_final",
]


class _OrderBase(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    my_role = serializers.SerializerMethodField()
    allowed_next = serializers.SerializerMethodField()
    next_step = serializers.SerializerMethodField()
    shipment = serializers.SerializerMethodField()
    delivery_map_url = serializers.SerializerMethodField()

    kind = ""

    def get_delivery_map_url(self, obj):
        return map_url(obj.delivery_latitude, obj.delivery_longitude)

    def _role(self, obj):
        user = self.context["request"].user
        return sales_role(user, obj) if isinstance(obj, SalesOrder) else purchase_role(user, obj)

    def get_my_role(self, obj):
        return self._role(obj)

    def get_allowed_next(self, obj):
        role = self._role(obj)
        if not role:
            return []
        model = type(obj)
        return [{"status": s, "label": model.Status(s).label} for s in allowed_next(obj, role)]

    def get_next_step(self, obj):
        return NEXT_STEP_HINTS[self.kind].get(obj.status, "")

    def get_shipment(self, obj):
        sh = getattr(obj, "shipment", None)
        if sh is None:
            return None
        return {"id": sh.pk, "status": sh.status, "status_display": sh.get_status_display(),
                "tracking_number": sh.tracking_number, "carrier": sh.display_carrier}


class SalesOrderSerializer(_OrderBase):
    kind = "sales"
    items = SalesItemSerializer(many=True, read_only=True)
    status_logs = StatusLogSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    review = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            "id", "status", "status_display", "next_step", "my_role", "allowed_next", "customer", "customer_name",
            "business", "business_name", "items", "subtotal", "total", "notes", "requested_date",
            *DELIVERY_FIELDS, "created_at", "updated_at", "completed_at", "status_logs", "shipment",
            "review", "can_review",
        ]

    def get_review(self, obj):
        r = getattr(obj, "review", None)
        if r is None:
            return None
        return {"id": r.pk, "rating": r.rating, "comment": r.comment, "created_at": r.created_at}

    def get_can_review(self, obj):
        user = self.context["request"].user
        return obj.customer_id == user.pk and obj.status == SalesOrder.Status.COMPLETED and not hasattr(obj, "review")


class SalesOrderListSerializer(_OrderBase):
    kind = "sales"
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id", "status", "status_display", "my_role", "customer_name", "business", "business_name",
            "items_count", "subtotal", "total", "fulfillment", "created_at",
        ]

    def get_allowed_next(self, obj):
        return []

    def get_shipment(self, obj):
        return None


class PurchaseOrderSerializer(_OrderBase):
    kind = "purchase"
    items = PurchaseItemSerializer(many=True, read_only=True)
    status_logs = StatusLogSerializer(many=True, read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "status", "status_display", "next_step", "my_role", "allowed_next", "business", "business_name",
            "supplier", "supplier_name", "items", "subtotal", "total", "notes", *DELIVERY_FIELDS,
            "created_at", "updated_at", "completed_at", "status_logs", "shipment",
        ]


class PurchaseOrderListSerializer(_OrderBase):
    kind = "purchase"
    business_name = serializers.CharField(source="business.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "status", "status_display", "my_role", "business_name", "supplier", "supplier_name",
            "items_count", "subtotal", "total", "fulfillment", "created_at",
        ]

    def get_allowed_next(self, obj):
        return []

    def get_shipment(self, obj):
        return None


class SalesItemInput(serializers.Serializer):
    offer_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class PurchaseItemInput(serializers.Serializer):
    material_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class SalesOrderCreateSerializer(serializers.Serializer):
    items = SalesItemInput(many=True, allow_empty=False)
    fulfillment = serializers.ChoiceField(choices=Fulfillment.choices)
    address_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    requested_date = serializers.DateField(required=False, allow_null=True)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    items = PurchaseItemInput(many=True, allow_empty=False)
    fulfillment = serializers.ChoiceField(choices=Fulfillment.choices)
    address_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class TransitionSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=20)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class DeliveryTermsSerializer(serializers.Serializer):
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, allow_null=True)
    delivery_payer = serializers.ChoiceField(choices=DeliveryPayer.choices)
    delivery_fee_is_final = serializers.BooleanField()

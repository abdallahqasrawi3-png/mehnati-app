from rest_framework import serializers

from .models import InventoryMovement


class StockAdjustSerializer(serializers.Serializer):
    delta = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="موجب للإضافة، سالب للخصم")
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class MovementSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = InventoryMovement
        fields = [
            "id", "kind", "kind_display", "quantity", "stock_after", "reserved_after",
            "sales_order", "purchase_order", "note", "created_at",
        ]

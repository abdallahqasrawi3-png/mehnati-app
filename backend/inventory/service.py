"""Stock operations for ready-made offers and raw materials.

Every change locks the item row (SELECT ... FOR UPDATE) inside a transaction,
so concurrent orders cannot reserve the same quantity twice, and database check
constraints guarantee quantities never become negative.
"""
from decimal import Decimal

from django.db import transaction

from catalog.models import Offer
from core.exceptions import BusinessRuleError
from notifications.models import Notification
from notifications.service import notify
from suppliers.models import Material

from .models import InventoryMovement


def _owner(item):
    if isinstance(item, Offer):
        return item.business.owner
    return item.supplier.owner


def _lock(item):
    model = type(item)
    qs = model.objects.select_for_update().filter(pk=item.pk)
    obj = qs.get()
    return obj


def _record(obj, kind, qty, order=None, actor=None, note=""):
    kwargs = {}
    if isinstance(obj, Offer):
        kwargs["offer"] = obj
    else:
        kwargs["material"] = obj
    if order is not None:
        if order.__class__.__name__ == "SalesOrder":
            kwargs["sales_order"] = order
        else:
            kwargs["purchase_order"] = order
    InventoryMovement.objects.create(
        kind=kind,
        quantity=Decimal(qty),
        stock_after=Decimal(obj.stock_quantity),
        reserved_after=Decimal(obj.reserved_quantity),
        actor=actor,
        note=note[:255],
        **kwargs,
    )


def _check_low_stock(obj, available_before):
    threshold = obj.low_stock_threshold or 0
    if threshold <= 0:
        return
    available_after = obj.stock_quantity - obj.reserved_quantity
    if available_after <= threshold < available_before:
        notify(
            _owner(obj),
            Notification.Kind.LOW_STOCK,
            f"انخفاض مخزون: {obj.title}",
            f"الكمية المتاحة الآن {available_after} وحد التنبيه {threshold}.",
            ref_type="offer" if isinstance(obj, Offer) else "material",
            ref_id=obj.pk,
        )


def _validate_qty(item, qty):
    if qty is None or Decimal(qty) <= 0:
        raise BusinessRuleError("الكمية يجب أن تكون أكبر من صفر.")
    if isinstance(item, Offer) and Decimal(qty) != Decimal(int(qty)):
        raise BusinessRuleError("كمية المنتج يجب أن تكون عددًا صحيحًا.")


def _cast(item, qty):
    return int(qty) if isinstance(item, Offer) else Decimal(qty)


def tracks_stock(item):
    return isinstance(item, Material) or (isinstance(item, Offer) and item.tracks_stock)


@transaction.atomic
def reserve(item, qty, *, order=None, actor=None):
    _validate_qty(item, qty)
    if not tracks_stock(item):
        return item
    obj = _lock(item)
    qty = _cast(obj, qty)
    available = obj.stock_quantity - obj.reserved_quantity
    if qty > available:
        raise BusinessRuleError(f"الكمية المطلوبة من «{obj.title}» غير متوفرة. المتاح: {available}.", "insufficient_stock")
    obj.reserved_quantity += qty
    obj.save(update_fields=["reserved_quantity", "updated_at"])
    _record(obj, InventoryMovement.Kind.RESERVE, qty, order, actor, "حجز لطلب")
    _check_low_stock(obj, available)
    return obj


@transaction.atomic
def release(item, qty, *, order=None, actor=None, note="تحرير حجز"):
    if not tracks_stock(item):
        return item
    obj = _lock(item)
    qty = _cast(obj, qty)
    if qty > obj.reserved_quantity:
        raise BusinessRuleError("لا يمكن تحرير كمية أكبر من المحجوز.")
    obj.reserved_quantity -= qty
    obj.save(update_fields=["reserved_quantity", "updated_at"])
    _record(obj, InventoryMovement.Kind.RELEASE, qty, order, actor, note)
    return obj


@transaction.atomic
def finalize_sale(item, qty, *, order=None, actor=None):
    """Turn a reservation into a sale: physical stock and reservation both drop."""
    if not tracks_stock(item):
        return item
    obj = _lock(item)
    qty = _cast(obj, qty)
    if qty > obj.reserved_quantity or qty > obj.stock_quantity:
        raise BusinessRuleError("بيانات المخزون غير متسقة لهذا الطلب.")
    available_before = obj.stock_quantity - obj.reserved_quantity
    obj.stock_quantity -= qty
    obj.reserved_quantity -= qty
    obj.save(update_fields=["stock_quantity", "reserved_quantity", "updated_at"])
    _record(obj, InventoryMovement.Kind.SALE, qty, order, actor, "إكمال بيع")
    _check_low_stock(obj, available_before + 0)
    return obj


@transaction.atomic
def adjust(item, delta, *, actor=None, note=""):
    """Owner adds (positive delta) or removes (negative delta) physical stock."""
    if not tracks_stock(item):
        raise BusinessRuleError("هذا العرض لا يستخدم المخزون (منتج حسب الطلب أو خدمة).")
    obj = _lock(item)
    delta = _cast(obj, delta)
    if delta == 0:
        raise BusinessRuleError("الكمية يجب ألا تكون صفرًا.")
    new_stock = obj.stock_quantity + delta
    if new_stock < obj.reserved_quantity:
        raise BusinessRuleError(
            f"لا يمكن أن يقل المخزون عن الكمية المحجوزة للطلبات ({obj.reserved_quantity}).", "negative_stock"
        )
    available_before = obj.stock_quantity - obj.reserved_quantity
    obj.stock_quantity = new_stock
    obj.save(update_fields=["stock_quantity", "updated_at"])
    kind = InventoryMovement.Kind.ADD if delta > 0 else InventoryMovement.Kind.REMOVE
    _record(obj, kind, abs(delta), None, actor, note or kind.label)
    _check_low_stock(obj, available_before)
    return obj

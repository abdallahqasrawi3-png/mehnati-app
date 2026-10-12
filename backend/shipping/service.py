import logging

from django.db import IntegrityError, transaction

from core.exceptions import BusinessRuleError
from notifications.models import Notification
from notifications.service import notify
from orders.models import Fulfillment, PurchaseOrder, SalesOrder

from .carriers import CarrierError, get_adapter
from .models import Carrier, Shipment, ShipmentEvent

logger = logging.getLogger(__name__)

SALES_SHIPPABLE = {"accepted", "preparing", "ready", "in_transit", "delivery_failed"}
PURCHASE_SHIPPABLE = {"accepted", "preparing", "shipped"}


def _load_order(kind, order_id):
    try:
        if kind == Shipment.Kind.SALES:
            order = SalesOrder.objects.select_related("business__owner", "customer").get(pk=order_id)
            return order, order.business.owner, order.customer, SALES_SHIPPABLE
        if kind == Shipment.Kind.PURCHASE:
            order = PurchaseOrder.objects.select_related("supplier__owner", "buyer").get(pk=order_id)
            return order, order.supplier.owner, order.buyer, PURCHASE_SHIPPABLE
    except (SalesOrder.DoesNotExist, PurchaseOrder.DoesNotExist):
        raise BusinessRuleError("الطلب غير موجود.", "not_found")
    raise BusinessRuleError("نوع الشحنة غير صحيح.")


def _try_external_create(shipment, adapter):
    """Call the carrier. Only mark confirmed after the carrier confirms."""
    try:
        result = adapter.create_shipment(shipment, shipment.idempotency_key)
    except CarrierError as e:
        shipment.status = Shipment.Status.PENDING_CARRIER
        shipment.last_error = str(e)[:255]
        shipment.external_confirmed = False
        return False
    except Exception:
        logger.exception("Carrier adapter crashed")
        shipment.status = Shipment.Status.PENDING_CARRIER
        shipment.last_error = "تعذر الاتصال بشركة التوصيل."
        shipment.external_confirmed = False
        return False
    if result.confirmed:
        shipment.external_confirmed = True
        shipment.external_reference = result.external_reference
        shipment.tracking_number = result.tracking_number or shipment.tracking_number
        if result.cost is not None:
            shipment.cost = result.cost
        if result.estimated_arrival:
            shipment.estimated_arrival = result.estimated_arrival
        shipment.status = Shipment.Status.CREATED
        shipment.last_error = ""
        return True
    shipment.status = Shipment.Status.PENDING_CARRIER
    return False


def create_shipment(user, *, kind, order_id, carrier_id=None, carrier_name="", tracking_number="",
                    cost=None, cost_is_final=False, estimated_arrival=None):
    order, sender, recipient, shippable = _load_order(kind, order_id)
    if sender.pk != user.pk:
        raise BusinessRuleError("البائع فقط يسجل شحنة هذا الطلب.", "forbidden")
    if order.fulfillment != Fulfillment.DELIVERY:
        raise BusinessRuleError("هذا الطلب بالاستلام وليس بالتوصيل.")
    if order.status not in shippable:
        raise BusinessRuleError("لا يمكن تسجيل شحنة لطلب في هذه الحالة.")

    existing = Shipment.objects.filter(**{f"{kind}_order": order}).first()
    if existing:
        return existing, False  # retries never create duplicates

    carrier = None
    if carrier_id:
        carrier = Carrier.objects.filter(pk=carrier_id, is_active=True).first()
        if carrier is None:
            raise BusinessRuleError("شركة التوصيل غير موجودة.")
    elif not carrier_name.strip():
        raise BusinessRuleError("اختر شركة التوصيل أو اكتب اسمها.")
    try:
        adapter = get_adapter(carrier)
    except CarrierError as e:
        raise BusinessRuleError(str(e))

    try:
        with transaction.atomic():
            shipment = Shipment.objects.create(
                kind=kind,
                sales_order=order if kind == Shipment.Kind.SALES else None,
                purchase_order=order if kind == Shipment.Kind.PURCHASE else None,
                sender=sender,
                recipient=recipient,
                carrier=carrier,
                carrier_name=carrier_name.strip()[:120],
                tracking_number=tracking_number.strip()[:80],
                cost=cost,
                cost_is_final=bool(cost_is_final),
                estimated_arrival=estimated_arrival,
                idempotency_key=f"{kind}-{order.pk}",
            )
    except IntegrityError:
        return Shipment.objects.get(**{f"{kind}_order": order}), False

    if adapter.supports("create"):
        _try_external_create(shipment, adapter)
        shipment.save()
    ShipmentEvent.objects.create(
        shipment=shipment, status=shipment.status,
        note="تسجيل الشحنة" + (" (تأكيد من شركة التوصيل)" if shipment.external_confirmed else ""),
    )
    notify(
        recipient, Notification.Kind.SHIPMENT, f"تم تسجيل شحنة لطلبك #{order.pk}",
        f"شركة التوصيل: {shipment.display_carrier}. رقم التتبع: {shipment.tracking_number or 'غير متوفر'}.",
        "shipment", shipment.pk,
    )
    return shipment, True


def retry_external(user, shipment):
    if shipment.sender_id != user.pk:
        raise BusinessRuleError("لا تملك صلاحية على هذه الشحنة.", "forbidden")
    if shipment.external_confirmed:
        return shipment
    try:
        adapter = get_adapter(shipment.carrier)
    except CarrierError as e:
        raise BusinessRuleError(str(e))
    if not adapter.supports("create"):
        raise BusinessRuleError("هذه الشحنة يدوية ولا تحتاج اتصالًا بشركة التوصيل.")
    ok = _try_external_create(shipment, adapter)
    shipment.save()
    if ok:
        ShipmentEvent.objects.create(shipment=shipment, status=shipment.status, note="تأكيد من شركة التوصيل", source="carrier")
    return shipment


def update_shipment(user, shipment, *, status, note="", tracking_number=None, cost=None, cost_is_final=None,
                    estimated_arrival=None):
    if shipment.sender_id != user.pk:
        raise BusinessRuleError("المرسل فقط يحدّث حالة الشحنة.", "forbidden")
    if status not in Shipment.Status.values or status == Shipment.Status.PENDING_CARRIER:
        raise BusinessRuleError("حالة الشحنة غير صحيحة.")
    if shipment.status in (Shipment.Status.DELIVERED, Shipment.Status.RETURNED) and status != shipment.status:
        raise BusinessRuleError("الشحنة منتهية ولا يمكن تغيير حالتها.")
    shipment.status = status
    if tracking_number is not None:
        shipment.tracking_number = tracking_number.strip()[:80]
    if cost is not None:
        shipment.cost = cost
    if cost_is_final is not None:
        shipment.cost_is_final = bool(cost_is_final)
    if estimated_arrival is not None:
        shipment.estimated_arrival = estimated_arrival
    shipment.save()
    ShipmentEvent.objects.create(shipment=shipment, status=status, note=note[:255])
    notify(
        shipment.recipient, Notification.Kind.SHIPMENT, f"تحديث الشحنة #{shipment.pk}",
        f"حالة الشحنة: {shipment.get_status_display()}.", "shipment", shipment.pk,
    )
    return shipment

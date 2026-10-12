"""Order creation and status changes. All rules are enforced here, on the server."""
from collections import OrderedDict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from accounts.models import Address
from catalog.models import BusinessProfile, Offer, ProfileStatus
from core.exceptions import BusinessRuleError
from inventory import service as stock
from notifications.models import Notification
from notifications.service import notify
from suppliers.models import Material, SupplierProfile

from .models import (
    DeliveryPayer,
    Fulfillment,
    OrderStatusLog,
    PurchaseOrder,
    PurchaseOrderItem,
    SalesOrder,
    SalesOrderItem,
)
from .workflow import (
    BUYER,
    PURCHASE_FINAL,
    PURCHASE_RELEASE,
    SALES_FINAL,
    SALES_RELEASE,
    SELLER,
    allowed_next,
)


def _merge_items(items, key):
    merged = {}
    for it in items:
        k = int(it[key])
        merged[k] = merged.get(k, Decimal("0")) + Decimal(str(it["quantity"]))
    if not merged:
        raise BusinessRuleError("يجب أن يحتوي الطلب على عنصر واحد على الأقل.")
    # Sorted ids => rows are always locked in the same order (no deadlocks).
    return OrderedDict(sorted(merged.items()))


def _apply_address(order, user, fulfillment, address_id):
    order.fulfillment = fulfillment
    if fulfillment == Fulfillment.DELIVERY:
        if not address_id:
            raise BusinessRuleError("اختر عنوان التوصيل.")
        try:
            addr = Address.objects.select_related("city", "area").get(pk=address_id, user=user)
        except Address.DoesNotExist:
            raise BusinessRuleError("عنوان التوصيل غير موجود.")
        order.recipient_name = addr.recipient_name
        order.recipient_phone = addr.phone
        order.delivery_city = addr.city.name
        order.delivery_area = addr.area.name if addr.area else ""
        order.delivery_address = addr.full_text[:500]
        order.delivery_landmark = addr.landmark
        order.delivery_latitude = addr.latitude
        order.delivery_longitude = addr.longitude


# ---------------------------------------------------------------- sales orders
@transaction.atomic
def create_sales_order(customer, *, items, fulfillment, address_id=None, notes="", requested_date=None):
    merged = _merge_items(items, "offer_id")
    offers = {
        o.pk: o
        for o in Offer.objects.select_related("business").filter(pk__in=merged.keys(), is_deleted=False)
    }
    if len(offers) != len(merged):
        raise BusinessRuleError("بعض العروض غير موجودة أو حُذفت.")
    businesses = {o.business_id for o in offers.values()}
    if len(businesses) != 1:
        raise BusinessRuleError("يجب أن يكون الطلب من مشروع منزلي واحد فقط.")
    business = BusinessProfile.objects.get(pk=businesses.pop())
    if business.status != ProfileStatus.ACTIVE:
        raise BusinessRuleError("هذا المشروع غير متاح حاليًا.")
    if business.owner_id == customer.pk:
        raise BusinessRuleError("لا يمكنك الطلب من مشروعك الخاص.")
    if fulfillment == Fulfillment.DELIVERY and not business.delivery_available:
        raise BusinessRuleError("هذا المشروع لا يوفر التوصيل.")
    if fulfillment == Fulfillment.PICKUP and not business.pickup_available:
        raise BusinessRuleError("هذا المشروع لا يوفر الاستلام من المكان.")

    order = SalesOrder(customer=customer, business=business, notes=notes or "", requested_date=requested_date, subtotal=0)
    _apply_address(order, customer, fulfillment, address_id)
    order.save()

    subtotal = Decimal("0")
    for offer_id, qty in merged.items():
        offer = offers[offer_id]
        if qty != int(qty) or qty < 1:
            raise BusinessRuleError("الكمية يجب أن تكون عددًا صحيحًا موجبًا.")
        qty = int(qty)
        if not offer.is_available:
            raise BusinessRuleError(f"«{offer.title}» غير متاح حاليًا.")
        reserved = False
        if offer.tracks_stock:
            stock.reserve(offer, qty, order=order, actor=customer)
            reserved = True
        line_total = offer.price * qty
        SalesOrderItem.objects.create(
            order=order,
            offer=offer,
            title=offer.title,
            offer_type=offer.offer_type,
            price_unit=offer.price_unit,
            unit_price=offer.price,
            unit_cost=offer.unit_cost,
            quantity=qty,
            line_total=line_total,
            stock_reserved=reserved,
        )
        subtotal += line_total
    order.subtotal = subtotal
    order.save(update_fields=["subtotal"])
    OrderStatusLog.objects.create(sales_order=order, to_status=order.status, actor=customer, note="إنشاء الطلب")
    notify(
        business.owner, Notification.Kind.NEW_ORDER, f"طلب جديد #{order.pk}",
        f"وصل طلب جديد من {customer.full_name} بقيمة {subtotal} ₪.", "sales_order", order.pk,
    )
    return order


def sales_role(user, order):
    if order.business.owner_id == user.pk:
        return SELLER
    if order.customer_id == user.pk:
        return BUYER
    return None


@transaction.atomic
def transition_sales_order(user, order_id, new_status, note=""):
    order = SalesOrder.objects.select_for_update().select_related("business").get(pk=order_id)
    role = sales_role(user, order)
    if role is None:
        raise BusinessRuleError("لا تملك صلاحية على هذا الطلب.", "forbidden")
    if new_status not in allowed_next(order, role):
        raise BusinessRuleError(
            f"لا يمكن نقل الطلب من «{order.get_status_display()}» إلى الحالة المطلوبة.", "invalid_transition"
        )
    old = order.status
    items = list(order.items.select_related("offer"))
    if new_status in SALES_RELEASE:
        for it in items:
            if it.stock_reserved and it.offer is not None:
                stock.release(it.offer, it.quantity, order=order, actor=user, note="تحرير بسبب رفض/إلغاء الطلب")
                it.stock_reserved = False
                it.save(update_fields=["stock_reserved"])
    if new_status == SalesOrder.Status.COMPLETED:
        for it in items:
            if it.stock_reserved and it.offer is not None:
                stock.finalize_sale(it.offer, it.quantity, order=order, actor=user)
                it.stock_reserved = False
                it.save(update_fields=["stock_reserved"])
        order.completed_at = timezone.now()
    order.status = new_status
    order.save(update_fields=["status", "completed_at", "updated_at"])
    OrderStatusLog.objects.create(sales_order=order, from_status=old, to_status=new_status, actor=user, note=note[:500])
    other = order.customer if role == SELLER else order.business.owner
    notify(
        other, Notification.Kind.ORDER_STATUS, f"تحديث الطلب #{order.pk}",
        f"أصبحت حالة الطلب: {order.get_status_display()}.", "sales_order", order.pk,
    )
    return order


# ------------------------------------------------------------- purchase orders
@transaction.atomic
def create_purchase_order(buyer, *, items, fulfillment, address_id=None, notes=""):
    business = getattr(buyer, "business_profile", None)
    if business is None or business.status != ProfileStatus.ACTIVE:
        raise BusinessRuleError("طلبات شراء المواد الخام متاحة لأصحاب المشاريع الفعالة فقط.")
    merged = _merge_items(items, "material_id")
    materials = {
        m.pk: m
        for m in Material.objects.select_related("supplier").filter(pk__in=merged.keys(), is_deleted=False)
    }
    if len(materials) != len(merged):
        raise BusinessRuleError("بعض المواد غير موجودة أو حُذفت.")
    suppliers = {m.supplier_id for m in materials.values()}
    if len(suppliers) != 1:
        raise BusinessRuleError("يجب أن يكون طلب الشراء من مورد واحد فقط.")
    supplier = SupplierProfile.objects.get(pk=suppliers.pop())
    if supplier.status != ProfileStatus.ACTIVE:
        raise BusinessRuleError("هذا المورد غير متاح حاليًا.")
    if supplier.owner_id == buyer.pk:
        raise BusinessRuleError("لا يمكنك الشراء من حساب المورد الخاص بك.")
    if fulfillment == Fulfillment.DELIVERY and not supplier.delivery_available:
        raise BusinessRuleError("هذا المورد لا يوفر التوصيل.")
    if fulfillment == Fulfillment.PICKUP and not supplier.pickup_available:
        raise BusinessRuleError("هذا المورد لا يوفر الاستلام.")

    order = PurchaseOrder(buyer=buyer, business=business, supplier=supplier, notes=notes or "", subtotal=0)
    _apply_address(order, buyer, fulfillment, address_id)
    if fulfillment == Fulfillment.DELIVERY and supplier.delivery_cost is not None:
        order.delivery_fee = supplier.delivery_cost
        order.delivery_payer = DeliveryPayer.BUYER
        order.delivery_fee_is_final = False
    order.save()

    subtotal = Decimal("0")
    for material_id, qty in merged.items():
        m = materials[material_id]
        if not m.is_available:
            raise BusinessRuleError(f"«{m.title}» غير متاحة حاليًا.")
        if qty < m.min_order_quantity:
            raise BusinessRuleError(
                f"الحد الأدنى لشراء «{m.title}» هو {m.min_order_quantity} {m.get_unit_display()}.", "below_minimum"
            )
        stock.reserve(m, qty, order=order, actor=buyer)
        line_total = (m.price * qty).quantize(Decimal("0.01"))
        PurchaseOrderItem.objects.create(
            order=order, material=m, title=m.title, unit=m.unit, unit_price=m.price,
            quantity=qty, line_total=line_total, stock_reserved=True,
        )
        subtotal += line_total
    order.subtotal = subtotal
    order.save(update_fields=["subtotal"])
    OrderStatusLog.objects.create(purchase_order=order, to_status=order.status, actor=buyer, note="إنشاء الطلب")
    notify(
        supplier.owner, Notification.Kind.NEW_ORDER, f"طلب شراء جديد #{order.pk}",
        f"طلب {business.name} مواد بقيمة {subtotal} ₪.", "purchase_order", order.pk,
    )
    return order


def purchase_role(user, order):
    if order.supplier.owner_id == user.pk:
        return SELLER
    if order.buyer_id == user.pk:
        return BUYER
    return None


@transaction.atomic
def transition_purchase_order(user, order_id, new_status, note=""):
    order = PurchaseOrder.objects.select_for_update().select_related("supplier").get(pk=order_id)
    role = purchase_role(user, order)
    if role is None:
        raise BusinessRuleError("لا تملك صلاحية على هذا الطلب.", "forbidden")
    if new_status not in allowed_next(order, role):
        raise BusinessRuleError(
            f"لا يمكن نقل الطلب من «{order.get_status_display()}» إلى الحالة المطلوبة.", "invalid_transition"
        )
    old = order.status
    items = list(order.items.select_related("material"))
    if new_status in PURCHASE_RELEASE:
        for it in items:
            if it.stock_reserved and it.material is not None:
                stock.release(it.material, it.quantity, order=order, actor=user, note="تحرير بسبب رفض/إلغاء الطلب")
                it.stock_reserved = False
                it.save(update_fields=["stock_reserved"])
    if new_status == PurchaseOrder.Status.SHIPPED:
        # Goods leave the supplier: reservation becomes a completed sale.
        for it in items:
            if it.stock_reserved and it.material is not None:
                stock.finalize_sale(it.material, it.quantity, order=order, actor=user)
                it.stock_reserved = False
                it.save(update_fields=["stock_reserved"])
    if new_status == PurchaseOrder.Status.RECEIVED:
        order.completed_at = timezone.now()
    order.status = new_status
    order.save(update_fields=["status", "completed_at", "updated_at"])
    OrderStatusLog.objects.create(purchase_order=order, from_status=old, to_status=new_status, actor=user, note=note[:500])
    other = order.buyer if role == SELLER else order.supplier.owner
    notify(
        other, Notification.Kind.ORDER_STATUS, f"تحديث طلب الشراء #{order.pk}",
        f"أصبحت حالة الطلب: {order.get_status_display()}.", "purchase_order", order.pk,
    )
    return order


# --------------------------------------------------------------- delivery fee
@transaction.atomic
def set_delivery_terms(user, order, *, delivery_fee, delivery_payer, delivery_fee_is_final):
    """Seller records delivery cost, who pays it and whether it is final."""
    is_sales = isinstance(order, SalesOrder)
    role = sales_role(user, order) if is_sales else purchase_role(user, order)
    if role != SELLER:
        raise BusinessRuleError("البائع فقط يحدد تكلفة التوصيل.", "forbidden")
    final = SALES_FINAL if is_sales else PURCHASE_FINAL
    if order.status in final:
        raise BusinessRuleError("لا يمكن تعديل التوصيل لطلب منتهٍ.")
    if order.fulfillment != Fulfillment.DELIVERY:
        raise BusinessRuleError("هذا الطلب بدون توصيل.")
    if delivery_fee is not None and Decimal(delivery_fee) < 0:
        raise BusinessRuleError("تكلفة التوصيل لا يمكن أن تكون سالبة.")
    order.delivery_fee = delivery_fee
    order.delivery_payer = delivery_payer
    order.delivery_fee_is_final = bool(delivery_fee_is_final)
    order.save(update_fields=["delivery_fee", "delivery_payer", "delivery_fee_is_final", "updated_at"])
    buyer = order.customer if is_sales else order.buyer
    notify(
        buyer, Notification.Kind.ORDER_STATUS, f"تحديث تكلفة التوصيل للطلب #{order.pk}",
        f"تكلفة التوصيل: {delivery_fee} ₪ ({'نهائية' if order.delivery_fee_is_final else 'تقديرية'}).",
        "sales_order" if is_sales else "purchase_order", order.pk,
    )
    return order

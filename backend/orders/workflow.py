"""Allowed order status transitions and who may perform them.

BUYER = customer (sales) or purchasing business owner (purchase)
SELLER = home-business owner (sales) or supplier (purchase)
"""
from .models import Fulfillment, PurchaseOrder, SalesOrder

BUYER = "buyer"
SELLER = "seller"

S = SalesOrder.Status
SALES_TRANSITIONS = {
    S.PENDING: {S.ACCEPTED: {SELLER}, S.REJECTED: {SELLER}, S.CANCELLED: {BUYER, SELLER}},
    S.ACCEPTED: {S.PREPARING: {SELLER}, S.CANCELLED: {SELLER}},
    S.PREPARING: {S.READY: {SELLER}, S.CANCELLED: {SELLER}},
    S.READY: {S.IN_TRANSIT: {SELLER}, S.COMPLETED: {SELLER}, S.CANCELLED: {SELLER}},
    S.IN_TRANSIT: {S.COMPLETED: {SELLER}, S.DELIVERY_FAILED: {SELLER}},
    S.DELIVERY_FAILED: {S.IN_TRANSIT: {SELLER}, S.CANCELLED: {SELLER}},
}
SALES_FINAL = {S.COMPLETED, S.REJECTED, S.CANCELLED}
SALES_RELEASE = {S.REJECTED, S.CANCELLED}

P = PurchaseOrder.Status
PURCHASE_TRANSITIONS = {
    P.PENDING: {P.ACCEPTED: {SELLER}, P.REJECTED: {SELLER}, P.CANCELLED: {BUYER, SELLER}},
    P.ACCEPTED: {P.PREPARING: {SELLER}, P.CANCELLED: {SELLER}},
    P.PREPARING: {P.SHIPPED: {SELLER}, P.CANCELLED: {SELLER}},
    P.SHIPPED: {P.RECEIVED: {BUYER}},
}
PURCHASE_FINAL = {P.RECEIVED, P.REJECTED, P.CANCELLED}
PURCHASE_RELEASE = {P.REJECTED, P.CANCELLED}

NEXT_STEP_HINTS = {
    "sales": {
        S.PENDING: "بانتظار قبول صاحب المشروع للطلب.",
        S.ACCEPTED: "قبل صاحب المشروع الطلب وسيبدأ التجهيز.",
        S.PREPARING: "الطلب قيد التجهيز.",
        S.READY: "الطلب جاهز؛ ينتظر الاستلام أو الشحن.",
        S.IN_TRANSIT: "الطلب في الطريق إليك.",
        S.DELIVERY_FAILED: "تعذر التسليم؛ سيعيد صاحب المشروع المحاولة أو يلغي الطلب.",
        S.COMPLETED: "اكتمل الطلب. يمكنك تقييم التجربة.",
        S.REJECTED: "رفض صاحب المشروع الطلب.",
        S.CANCELLED: "أُلغي الطلب.",
    },
    "purchase": {
        P.PENDING: "بانتظار قبول المورد للطلب.",
        P.ACCEPTED: "قبل المورد الطلب.",
        P.PREPARING: "المورد يجهز الطلب.",
        P.SHIPPED: "تم الشحن أو أصبح جاهزًا للاستلام؛ أكّد الاستلام عند وصوله.",
        P.RECEIVED: "تم استلام المواد.",
        P.REJECTED: "رفض المورد الطلب.",
        P.CANCELLED: "أُلغي الطلب.",
    },
}


def allowed_next(order, role):
    """List of statuses the given role may move this order to."""
    if isinstance(order, SalesOrder):
        options = SALES_TRANSITIONS.get(order.status, {})
    else:
        options = PURCHASE_TRANSITIONS.get(order.status, {})
    result = []
    for target, roles in options.items():
        if role not in roles:
            continue
        if isinstance(order, SalesOrder) and order.status == S.READY:
            if target == S.IN_TRANSIT and order.fulfillment != Fulfillment.DELIVERY:
                continue
            if target == S.COMPLETED and order.fulfillment != Fulfillment.PICKUP:
                continue
        result.append(target)
    return result

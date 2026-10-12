"""Financial reports. All money is calculated here in code (Decimal), never by AI."""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from catalog.models import BusinessProfile, Offer
from core.exceptions import BusinessRuleError
from core.models import AbuseReport
from orders.models import DeliveryPayer, PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem
from suppliers.models import Material, SupplierProfile

from .models import Expense

ZERO = Decimal("0.00")
PERIOD_LABELS = {"day": "اليوم", "week": "آخر 7 أيام", "month": "آخر 30 يومًا"}


def period_range(period="month", date_from=None, date_to=None):
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    if date_from and date_to:
        start_d, end_d = date_from, date_to
        label = f"من {start_d} إلى {end_d}"
    else:
        if period not in PERIOD_LABELS:
            raise BusinessRuleError("الفترة يجب أن تكون day أو week أو month.")
        days = {"day": 0, "week": 6, "month": 29}[period]
        start_d, end_d = today - timedelta(days=days), today
        label = PERIOD_LABELS[period]
    if start_d > end_d:
        raise BusinessRuleError("تاريخ البداية بعد تاريخ النهاية.")
    start = timezone.make_aware(datetime.combine(start_d, time.min), tz)
    end = timezone.make_aware(datetime.combine(end_d + timedelta(days=1), time.min), tz)
    return start, end, start_d, end_d, label


def _money(v):
    return (v or ZERO).quantize(Decimal("0.01"))


def business_report(business: BusinessProfile, period="month", date_from=None, date_to=None):
    start, end, start_d, end_d, label = period_range(period, date_from, date_to)
    completed = SalesOrder.objects.filter(
        business=business, status=SalesOrder.Status.COMPLETED, completed_at__gte=start, completed_at__lt=end
    )
    items = SalesOrderItem.objects.filter(order__in=completed)
    revenue = _money(items.aggregate(s=Sum("line_total"))["s"])
    cost_expr = ExpressionWrapper(F("unit_cost") * F("quantity"), output_field=DecimalField(max_digits=14, decimal_places=2))
    cogs = _money(items.filter(unit_cost__isnull=False).aggregate(s=Sum(cost_expr))["s"])
    items_missing_cost = items.filter(unit_cost__isnull=True).count()

    business_delivery = _money(
        completed.filter(delivery_payer=DeliveryPayer.SELLER, delivery_fee__isnull=False).aggregate(s=Sum("delivery_fee"))["s"]
    )
    expenses_qs = Expense.objects.filter(business=business, date__gte=start_d, date__lte=end_d)
    expenses_total = _money(expenses_qs.aggregate(s=Sum("amount"))["s"])
    expenses_by_cat = [
        {"category": row["category"], "label": Expense.Category(row["category"]).label, "amount": _money(row["s"])}
        for row in expenses_qs.values("category").annotate(s=Sum("amount")).order_by("-s")
    ]
    profit = revenue - cogs - expenses_total - business_delivery

    best = (
        items.values("title")
        .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-quantity", "-revenue")[:5]
    )
    daily = (
        completed.annotate(day=TruncDate("completed_at"))
        .values("day")
        .annotate(orders=Count("id"), revenue=Sum("subtotal"))
        .order_by("day")
    )
    purchases = PurchaseOrder.objects.filter(
        business=business, status=PurchaseOrder.Status.RECEIVED, completed_at__gte=start, completed_at__lt=end
    )
    purchases_total = _money(purchases.aggregate(s=Sum("subtotal"))["s"])

    open_statuses = [SalesOrder.Status.PENDING, SalesOrder.Status.ACCEPTED, SalesOrder.Status.PREPARING,
                     SalesOrder.Status.READY, SalesOrder.Status.IN_TRANSIT, SalesOrder.Status.DELIVERY_FAILED]
    low_stock = Offer.objects.filter(
        business=business, is_deleted=False, offer_type=Offer.OfferType.READY, low_stock_threshold__gt=0,
        stock_quantity__lte=F("reserved_quantity") + F("low_stock_threshold"),
    ).count()

    costs_incomplete = items_missing_cost > 0
    notes = ["الربح تقديري ويعتمد على اكتمال التكاليف والمصاريف المسجلة."]
    if costs_incomplete:
        notes.append(f"{items_missing_cost} عنصرًا مباعًا بلا تكلفة مسجلة، لذلك الربح الفعلي قد يكون أقل.")
    notes.append("مشتريات المواد الخام معروضة منفصلة ولا تُخصم تلقائيًا من الربح؛ سجّل المواد المستهلكة كمصروف.")

    return {
        "period": {"key": period, "label": label, "start": start_d, "end": end_d},
        "completed_orders": completed.count(),
        "revenue": revenue,
        "cost_of_goods_sold": cogs,
        "items_missing_cost": items_missing_cost,
        "expenses_total": expenses_total,
        "expenses_by_category": expenses_by_cat,
        "delivery_paid_by_business": business_delivery,
        "estimated_operating_profit": _money(profit),
        "costs_incomplete": costs_incomplete,
        "best_sellers": [
            {"title": b["title"], "quantity": b["quantity"], "revenue": _money(b["revenue"])} for b in best
        ],
        "daily": [{"date": d["day"], "orders": d["orders"], "revenue": _money(d["revenue"])} for d in daily],
        "raw_material_purchases": {"received_orders": purchases.count(), "total": purchases_total},
        "open_orders": SalesOrder.objects.filter(business=business, status__in=open_statuses).count(),
        "low_stock_items": low_stock,
        "formula": "صافي الربح التشغيلي التقديري = إيرادات الطلبات المكتملة − تكلفة المنتجات/الخدمات المباعة − المصاريف المباشرة المسجلة (ومنها التوصيل على حساب المشروع)",
        "notes": notes,
    }


def supplier_report(supplier: SupplierProfile, period="month", date_from=None, date_to=None):
    start, end, start_d, end_d, label = period_range(period, date_from, date_to)
    received = PurchaseOrder.objects.filter(
        supplier=supplier, status=PurchaseOrder.Status.RECEIVED, completed_at__gte=start, completed_at__lt=end
    )
    items = PurchaseOrderItem.objects.filter(order__in=received)
    revenue = _money(items.aggregate(s=Sum("line_total"))["s"])
    best = (
        items.values("title", "unit")
        .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-revenue")[:5]
    )
    shipped_waiting = PurchaseOrder.objects.filter(supplier=supplier, status=PurchaseOrder.Status.SHIPPED)
    open_statuses = [PurchaseOrder.Status.PENDING, PurchaseOrder.Status.ACCEPTED, PurchaseOrder.Status.PREPARING]
    low_stock = Material.objects.filter(
        supplier=supplier, is_deleted=False, low_stock_threshold__gt=0,
        stock_quantity__lte=F("reserved_quantity") + F("low_stock_threshold"),
    ).count()
    return {
        "period": {"key": period, "label": label, "start": start_d, "end": end_d},
        "completed_orders": received.count(),
        "revenue": revenue,
        "best_materials": [
            {"title": b["title"], "unit": Material.Unit(b["unit"]).label, "quantity": b["quantity"], "revenue": _money(b["revenue"])}
            for b in best
        ],
        "shipped_awaiting_confirmation": {
            "orders": shipped_waiting.count(),
            "total": _money(shipped_waiting.aggregate(s=Sum("subtotal"))["s"]),
        },
        "open_orders": PurchaseOrder.objects.filter(supplier=supplier, status__in=open_statuses).count(),
        "low_stock_items": low_stock,
        "notes": ["تقارير المورد منفصلة تمامًا عن مبيعات أصحاب المشاريع.", "تُحسب المبيعات المكتملة عند تأكيد المشتري للاستلام."],
    }


def admin_indicators():
    from accounts.models import User

    return {
        "users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "businesses": BusinessProfile.objects.count(),
        "suppliers": SupplierProfile.objects.count(),
        "offers": Offer.objects.filter(is_deleted=False).count(),
        "materials": Material.objects.filter(is_deleted=False).count(),
        "sales_orders_by_status": {
            row["status"]: row["n"] for row in SalesOrder.objects.values("status").annotate(n=Count("id"))
        },
        "purchase_orders_by_status": {
            row["status"]: row["n"] for row in PurchaseOrder.objects.values("status").annotate(n=Count("id"))
        },
        "completed_sales_value": _money(
            SalesOrder.objects.filter(status=SalesOrder.Status.COMPLETED).aggregate(s=Sum("subtotal"))["s"]
        ),
        "open_abuse_reports": AbuseReport.objects.filter(status=AbuseReport.Status.OPEN).count(),
        "suspended_profiles": BusinessProfile.objects.filter(status="suspended").count()
        + SupplierProfile.objects.filter(status="suspended").count(),
    }

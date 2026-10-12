from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.testutils import World, client_for
from orders import service as orders
from reports.models import Expense
from reports.service import business_report


class ReportTests(TestCase):
    def setUp(self):
        self.w = World()

    def sell(self, offer, qty, payer=None, fee=None):
        kw = {"fulfillment": "pickup"}
        if payer:
            kw = {"fulfillment": "delivery", "address_id": self.w.address.pk}
        o = orders.create_sales_order(self.w.customer, items=[{"offer_id": offer.pk, "quantity": qty}], **kw)
        if payer:
            orders.set_delivery_terms(self.w.owner, o, delivery_fee=Decimal(fee), delivery_payer=payer, delivery_fee_is_final=True)
        steps = ["accepted", "preparing", "ready"] + (["in_transit"] if payer else []) + ["completed"]
        for st in steps:
            orders.transition_sales_order(self.w.owner, o.pk, st)
        return o

    def test_profit_calculation(self):
        self.sell(self.w.ready, 2)                       # revenue 160, cost 60
        self.sell(self.w.custom, 1, payer="seller", fee="10")  # revenue 400, cost unknown, delivery 10 by business
        orders.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="pickup")  # not completed
        Expense.objects.create(business=self.w.business, date=timezone.localdate(), category="packaging", amount=Decimal("15"))
        rep = business_report(self.w.business, "month")
        self.assertEqual(rep["completed_orders"], 2)
        self.assertEqual(rep["revenue"], Decimal("560.00"))
        self.assertEqual(rep["cost_of_goods_sold"], Decimal("60.00"))
        self.assertEqual(rep["expenses_total"], Decimal("15.00"))
        self.assertEqual(rep["delivery_paid_by_business"], Decimal("10.00"))
        self.assertEqual(rep["estimated_operating_profit"], Decimal("475.00"))
        self.assertTrue(rep["costs_incomplete"])
        self.assertEqual(rep["items_missing_cost"], 1)
        self.assertEqual(rep["best_sellers"][0]["title"], "طارة مطرزة هدية")
        self.assertEqual(rep["open_orders"], 1)

    def test_purchases_shown_separately_not_deducted(self):
        self.sell(self.w.ready, 1)
        po = orders.create_purchase_order(self.w.owner, items=[{"material_id": self.w.fabric.pk, "quantity": "5"}], fulfillment="pickup")
        for st in ["accepted", "preparing", "shipped"]:
            orders.transition_purchase_order(self.w.supplier_user, po.pk, st)
        orders.transition_purchase_order(self.w.owner, po.pk, "received")
        rep = business_report(self.w.business, "week")
        self.assertEqual(rep["raw_material_purchases"]["total"], Decimal("90.00"))
        self.assertEqual(rep["estimated_operating_profit"], Decimal("50.00"))  # 80 - 30, purchases not deducted

    def test_report_permissions_and_separation(self):
        self.sell(self.w.ready, 1)
        r = client_for(self.w.owner2).get("/api/reports/business/")
        self.assertEqual(Decimal(r.data["revenue"]), Decimal("0"))  # owner2 sees only own figures
        self.assertEqual(client_for(self.w.customer).get("/api/reports/business/").status_code, 403)
        self.assertEqual(client_for(self.w.owner).get("/api/reports/supplier/").status_code, 403)
        r = client_for(self.w.supplier_user).get("/api/reports/supplier/", {"period": "day"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(r.data["revenue"]), Decimal("0"))

    def test_expenses_are_private(self):
        e = Expense.objects.create(business=self.w.business, date=timezone.localdate(), amount=Decimal("5"))
        self.assertEqual(client_for(self.w.owner2).get(f"/api/expenses/{e.pk}/").status_code, 404)
        self.assertEqual(client_for(self.w.owner).get(f"/api/expenses/{e.pk}/").status_code, 200)

    def test_admin_indicators(self):
        r = client_for(self.w.admin).get("/api/reports/admin/")
        self.assertEqual(r.data["businesses"], 2)

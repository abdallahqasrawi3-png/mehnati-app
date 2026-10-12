import threading
from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase

from catalog.models import Offer
from core.exceptions import BusinessRuleError
from core.testutils import World, client_for
from inventory import service as stock
from notifications.models import Notification
from orders import service as orders
from orders.models import SalesOrder


class StockRulesTests(TestCase):
    def setUp(self):
        self.w = World()

    def test_cannot_reduce_stock_below_reserved_or_zero(self):
        orders.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 2}], fulfillment="pickup")
        with self.assertRaises(BusinessRuleError):
            stock.adjust(self.w.ready, -2, actor=self.w.owner)  # 3 on hand, 2 reserved
        stock.adjust(self.w.ready, -1, actor=self.w.owner)
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.stock_quantity, 2)

    def test_database_constraint_blocks_negative_values(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Offer.objects.filter(pk=self.w.ready.pk).update(reserved_quantity=10)

    def test_stock_endpoint_logs_movement_and_rejects_services(self):
        c = client_for(self.w.owner)
        r = c.post(f"/api/my/offers/{self.w.ready.pk}/stock/", {"delta": "5", "note": "إنتاج جديد"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["stock_quantity"], 8)
        r = c.get(f"/api/my/offers/{self.w.ready.pk}/movements/")
        self.assertEqual(r.data[0]["kind"], "add")
        r = c.post(f"/api/my/offers/{self.w.custom.pk}/stock/", {"delta": "5"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_low_stock_alert(self):
        with self.captureOnCommitCallbacks(execute=True):
            orders.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 2}], fulfillment="pickup")
        self.assertTrue(Notification.objects.filter(user=self.w.owner, kind="low_stock").exists())
        r = client_for(self.w.owner).get("/api/inventory/low-stock/")
        self.assertEqual(r.data["offers"][0]["id"], self.w.ready.pk)

    def test_material_quantities_are_decimal_and_safe(self):
        with self.assertRaises(BusinessRuleError):
            stock.reserve(self.w.fabric, Decimal("20.5"))
        stock.reserve(self.w.fabric, Decimal("19.75"))
        self.w.fabric.refresh_from_db()
        self.assertEqual(self.w.fabric.available_quantity, Decimal("0.25"))


class ConcurrentReservationTests(TransactionTestCase):
    """Two customers try to buy the last unit at the same moment."""

    def test_only_one_order_gets_the_last_unit(self):
        w = World()
        stock.adjust(w.ready, -2, actor=w.owner)  # leave exactly 1 unit
        barrier = threading.Barrier(4)
        results = []

        def attempt(user):
            try:
                barrier.wait()
                orders.create_sales_order(user, items=[{"offer_id": w.ready.pk, "quantity": 1}], fulfillment="pickup")
                results.append("ok")
            except BusinessRuleError:
                results.append("rejected")
            finally:
                connection.close()

        buyers = [w.customer, w.customer2, w.owner2, w.supplier_user]
        threads = [threading.Thread(target=attempt, args=(u,)) for u in buyers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count("ok"), 1, results)
        self.assertEqual(results.count("rejected"), 3, results)
        w.ready.refresh_from_db()
        self.assertEqual(w.ready.reserved_quantity, 1)
        self.assertEqual(w.ready.stock_quantity, 1)
        self.assertEqual(SalesOrder.objects.count(), 1)

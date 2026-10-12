from decimal import Decimal

from django.test import TestCase

from core.exceptions import BusinessRuleError
from core.testutils import World, client_for
from inventory.models import InventoryMovement
from notifications.models import Notification
from orders import service
from orders.models import PurchaseOrder, SalesOrder


class SalesOrderTests(TestCase):
    def setUp(self):
        self.w = World()

    def create(self, user=None, items=None, **kw):
        body = {"items": items or [{"offer_id": self.w.ready.pk, "quantity": 2}], "fulfillment": "pickup", **kw}
        return client_for(user or self.w.customer).post("/api/sales-orders/", body, format="json")

    def test_create_order_snapshots_prices_and_reserves_stock(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.create()
        self.assertEqual(r.status_code, 201, r.content)
        order = SalesOrder.objects.get(pk=r.data["id"])
        self.assertEqual(order.subtotal, Decimal("160"))
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.reserved_quantity, 2)
        self.assertEqual(self.w.ready.stock_quantity, 3)
        # Snapshot does not change when the owner edits the offer later
        self.w.ready.price = Decimal("999")
        self.w.ready.save()
        self.assertEqual(order.items.get().unit_price, Decimal("80"))
        self.assertTrue(Notification.objects.filter(user=self.w.owner, kind="new_order").exists())

    def test_cannot_order_more_than_available(self):
        r = self.create(items=[{"offer_id": self.w.ready.pk, "quantity": 4}])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(SalesOrder.objects.count(), 0)
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.reserved_quantity, 0)

    def test_one_business_per_order(self):
        r = self.create(items=[{"offer_id": self.w.ready.pk, "quantity": 1}, {"offer_id": self.w.food.pk, "quantity": 1}])
        self.assertEqual(r.status_code, 400)

    def test_delivery_requires_business_support_and_own_address(self):
        r = self.create(items=[{"offer_id": self.w.food.pk, "quantity": 1}], fulfillment="delivery", address_id=self.w.address.pk)
        self.assertEqual(r.status_code, 400)  # business2 has no delivery
        r = self.create(user=self.w.customer2, fulfillment="delivery", address_id=self.w.address.pk)
        self.assertEqual(r.status_code, 400)  # someone else's address
        r = self.create(fulfillment="delivery", address_id=self.w.address.pk)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["delivery_city"], "نابلس")

    def test_owner_cannot_order_from_own_business(self):
        self.assertEqual(self.create(user=self.w.owner).status_code, 400)

    def test_full_lifecycle_completes_sale_and_records_movements(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 2}], fulfillment="pickup")
        c = client_for(self.w.owner)
        for st in ["accepted", "preparing", "ready", "completed"]:
            r = c.post(f"/api/sales-orders/{order.pk}/transition/", {"status": st}, format="json")
            self.assertEqual(r.status_code, 200, (st, r.content))
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.stock_quantity, 1)
        self.assertEqual(self.w.ready.reserved_quantity, 0)
        kinds = list(InventoryMovement.objects.filter(offer=self.w.ready).values_list("kind", flat=True))
        self.assertIn("reserve", kinds)
        self.assertIn("sale", kinds)
        order.refresh_from_db()
        self.assertIsNotNone(order.completed_at)
        self.assertEqual(order.status_logs.count(), 5)

    def test_invalid_transitions_are_blocked(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="pickup")
        c = client_for(self.w.owner)
        self.assertEqual(c.post(f"/api/sales-orders/{order.pk}/transition/", {"status": "completed"}, format="json").status_code, 400)
        # Pickup orders never go "in transit"
        for st in ["accepted", "preparing", "ready"]:
            service.transition_sales_order(self.w.owner, order.pk, st)
        self.assertEqual(c.post(f"/api/sales-orders/{order.pk}/transition/", {"status": "in_transit"}, format="json").status_code, 400)

    def test_customer_can_cancel_only_while_pending_and_stock_is_released(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 2}], fulfillment="pickup")
        c = client_for(self.w.customer)
        # Customer cannot accept their own order
        self.assertEqual(c.post(f"/api/sales-orders/{order.pk}/transition/", {"status": "accepted"}, format="json").status_code, 400)
        r = c.post(f"/api/sales-orders/{order.pk}/transition/", {"status": "cancelled"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.reserved_quantity, 0)
        self.assertEqual(self.w.ready.stock_quantity, 3)
        self.assertTrue(InventoryMovement.objects.filter(offer=self.w.ready, kind="release").exists())

        order2 = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="pickup")
        service.transition_sales_order(self.w.owner, order2.pk, "accepted")
        with self.assertRaises(BusinessRuleError):
            service.transition_sales_order(self.w.customer, order2.pk, "cancelled")

    def test_rejection_releases_stock(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 3}], fulfillment="pickup")
        service.transition_sales_order(self.w.owner, order.pk, "rejected")
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.available_quantity, 3)

    def test_made_to_order_and_service_do_not_use_stock(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.custom.pk, "quantity": 5}], fulfillment="pickup")
        self.assertFalse(order.items.get().stock_reserved)
        self.w.custom.refresh_from_db()
        self.assertEqual(self.w.custom.reserved_quantity, 0)

    def test_order_privacy(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="delivery", address_id=self.w.address.pk)
        self.assertEqual(client_for(self.w.customer2).get(f"/api/sales-orders/{order.pk}/").status_code, 404)
        self.assertEqual(client_for(self.w.owner2).get(f"/api/sales-orders/{order.pk}/").status_code, 404)
        self.assertEqual(client_for(self.w.owner2).post(f"/api/sales-orders/{order.pk}/transition/", {"status": "accepted"}, format="json").status_code, 404)
        self.assertEqual(client_for().get(f"/api/sales-orders/{order.pk}/").status_code, 401)
        r = client_for(self.w.owner).get(f"/api/sales-orders/{order.pk}/")
        self.assertEqual(r.data["recipient_phone"], "0590000000")  # the seller needs it to deliver
        self.assertEqual(client_for(self.w.customer2).get("/api/sales-orders/").data["count"], 0)

    def test_delivery_terms_set_by_seller_only(self):
        order = service.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="delivery", address_id=self.w.address.pk)
        body = {"delivery_fee": "20", "delivery_payer": "buyer", "delivery_fee_is_final": False}
        self.assertEqual(client_for(self.w.customer).post(f"/api/sales-orders/{order.pk}/delivery/", body, format="json").status_code, 400)
        r = client_for(self.w.owner).post(f"/api/sales-orders/{order.pk}/delivery/", body, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Decimal(r.data["total"]), Decimal("100"))
        self.assertFalse(r.data["delivery_fee_is_final"])


class PurchaseOrderTests(TestCase):
    def setUp(self):
        self.w = World()

    def test_only_business_owners_can_buy_materials(self):
        r = client_for(self.w.customer).post("/api/purchase-orders/", {
            "items": [{"material_id": self.w.fabric.pk, "quantity": "3"}], "fulfillment": "pickup"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_minimum_quantity_enforced(self):
        r = client_for(self.w.owner).post("/api/purchase-orders/", {
            "items": [{"material_id": self.w.fabric.pk, "quantity": "1.5"}], "fulfillment": "pickup"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["code"], "below_minimum")

    def test_purchase_lifecycle(self):
        r = client_for(self.w.owner).post("/api/purchase-orders/", {
            "items": [{"material_id": self.w.fabric.pk, "quantity": "2.5"}], "fulfillment": "pickup"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        pid = r.data["id"]
        self.assertEqual(Decimal(r.data["subtotal"]), Decimal("45.00"))
        self.w.fabric.refresh_from_db()
        self.assertEqual(self.w.fabric.reserved_quantity, Decimal("2.5"))
        sup = client_for(self.w.supplier_user)
        for st in ["accepted", "preparing", "shipped"]:
            self.assertEqual(sup.post(f"/api/purchase-orders/{pid}/transition/", {"status": st}, format="json").status_code, 200)
        # Only the buyer confirms receipt
        self.assertEqual(sup.post(f"/api/purchase-orders/{pid}/transition/", {"status": "received"}, format="json").status_code, 400)
        self.assertEqual(client_for(self.w.owner).post(f"/api/purchase-orders/{pid}/transition/", {"status": "received"}, format="json").status_code, 200)
        self.w.fabric.refresh_from_db()
        self.assertEqual(self.w.fabric.stock_quantity, Decimal("17.5"))
        self.assertEqual(self.w.fabric.reserved_quantity, Decimal("0"))
        self.assertEqual(PurchaseOrder.objects.get(pk=pid).status, "received")

    def test_purchase_privacy_and_cancel_release(self):
        order = service.create_purchase_order(self.w.owner, items=[{"material_id": self.w.fabric.pk, "quantity": "4"}], fulfillment="pickup")
        self.assertEqual(client_for(self.w.owner2).get(f"/api/purchase-orders/{order.pk}/").status_code, 404)
        self.assertEqual(client_for(self.w.customer).get(f"/api/purchase-orders/{order.pk}/").status_code, 404)
        service.transition_purchase_order(self.w.owner, order.pk, "cancelled")
        self.w.fabric.refresh_from_db()
        self.assertEqual(self.w.fabric.reserved_quantity, Decimal("0"))

    def test_supplier_cannot_buy_from_self(self):
        from catalog.models import BusinessProfile

        BusinessProfile.objects.create(owner=self.w.supplier_user, name="x", category=self.w.cat_emb, city=self.w.nablus)
        with self.assertRaises(BusinessRuleError):
            service.create_purchase_order(self.w.supplier_user, items=[{"material_id": self.w.fabric.pk, "quantity": "2"}], fulfillment="pickup")

from django.test import TestCase, override_settings

from core.testutils import World, client_for
from orders import service as orders
from shipping.carriers import SimulatorAdapter
from shipping.models import Carrier, Shipment


class ShipmentTests(TestCase):
    def setUp(self):
        self.w = World()
        self.order = orders.create_sales_order(
            self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="delivery",
            address_id=self.w.address.pk,
        )
        orders.transition_sales_order(self.w.owner, self.order.pk, "accepted")

    def body(self, **kw):
        return {"kind": "sales", "order_id": self.order.pk, "carrier_name": "شركة توصيل محلية", "tracking_number": "TRK1", **kw}

    def test_manual_shipment_linked_to_correct_order(self):
        r = client_for(self.w.owner).post("/api/shipments/", self.body(cost="20"), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        sh = Shipment.objects.get(pk=r.data["id"])
        self.assertEqual(sh.sales_order_id, self.order.pk)
        self.assertEqual(sh.recipient, self.w.customer)
        self.assertFalse(sh.external_confirmed)  # manual: never claims carrier confirmation
        r = client_for(self.w.owner).post(f"/api/shipments/{sh.pk}/update_status/", {"status": "in_transit", "note": "خرجت"}, format="json")
        self.assertEqual(r.data["status"], "in_transit")
        self.assertEqual(len(r.data["events"]), 2)

    def test_no_duplicate_shipments(self):
        c = client_for(self.w.owner)
        r1 = c.post("/api/shipments/", self.body(), format="json")
        r2 = c.post("/api/shipments/", self.body(), format="json")
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.data["id"], r2.data["id"])
        self.assertEqual(Shipment.objects.count(), 1)

    def test_shipment_ownership(self):
        self.assertEqual(client_for(self.w.customer).post("/api/shipments/", self.body(), format="json").status_code, 400)
        self.assertEqual(client_for(self.w.owner2).post("/api/shipments/", self.body(), format="json").status_code, 400)
        sh_id = client_for(self.w.owner).post("/api/shipments/", self.body(), format="json").data["id"]
        # Recipient can view but not change; strangers cannot view
        self.assertEqual(client_for(self.w.customer).get(f"/api/shipments/{sh_id}/").status_code, 200)
        self.assertEqual(client_for(self.w.customer).post(f"/api/shipments/{sh_id}/update_status/", {"status": "delivered"}, format="json").status_code, 400)
        self.assertEqual(client_for(self.w.customer2).get(f"/api/shipments/{sh_id}/").status_code, 404)

    def test_pickup_orders_cannot_have_shipments(self):
        o = orders.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="pickup")
        orders.transition_sales_order(self.w.owner, o.pk, "accepted")
        r = client_for(self.w.owner).post("/api/shipments/", {**self.body(), "order_id": o.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    @override_settings(SHIPPING_SIMULATOR_ENABLED=True)
    def test_carrier_failure_then_retry_without_duplicates(self):
        carrier = Carrier.objects.create(name="محاكي اختبار", integration="simulator")
        SimulatorAdapter.fail_next = True
        try:
            r = client_for(self.w.owner).post("/api/shipments/", {"kind": "sales", "order_id": self.order.pk, "carrier_id": carrier.pk}, format="json")
        finally:
            SimulatorAdapter.fail_next = False
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["status"], "pending_carrier")
        self.assertFalse(r.data["external_confirmed"])
        self.assertTrue(r.data["last_error"])
        sh_id = r.data["id"]
        r = client_for(self.w.owner).post(f"/api/shipments/{sh_id}/retry/", format="json")
        self.assertTrue(r.data["external_confirmed"])
        ref = r.data["tracking_number"]
        r = client_for(self.w.owner).post(f"/api/shipments/{sh_id}/retry/", format="json")
        self.assertEqual(r.data["tracking_number"], ref)
        self.assertEqual(Shipment.objects.count(), 1)

    def test_simulator_refuses_when_disabled(self):
        carrier = Carrier.objects.create(name="محاكي", integration="simulator")
        r = client_for(self.w.owner).post("/api/shipments/", {"kind": "sales", "order_id": self.order.pk, "carrier_id": carrier.pk}, format="json")
        self.assertEqual(r.data["status"], "pending_carrier")
        self.assertFalse(r.data["external_confirmed"])

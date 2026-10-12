from decimal import Decimal

from django.test import TestCase

from core.models import AbuseReport
from core.testutils import World, client_for
from orders import service as orders


class ReviewTests(TestCase):
    def setUp(self):
        self.w = World()
        self.order = orders.create_sales_order(self.w.customer, items=[{"offer_id": self.w.ready.pk, "quantity": 1}], fulfillment="pickup")

    def complete(self):
        for st in ["accepted", "preparing", "ready", "completed"]:
            orders.transition_sales_order(self.w.owner, self.order.pk, st)

    def test_review_only_after_completion_and_once(self):
        c = client_for(self.w.customer)
        r = c.post("/api/reviews/", {"order": self.order.pk, "rating": 5, "comment": "ممتاز"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.complete()
        r = c.post("/api/reviews/", {"order": self.order.pk, "rating": 5, "comment": "ممتاز"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        r = c.post("/api/reviews/", {"order": self.order.pk, "rating": 1}, format="json")
        self.assertEqual(r.status_code, 400)
        self.w.business.refresh_from_db()
        self.assertEqual(self.w.business.rating_avg, Decimal("5"))
        self.assertEqual(self.w.business.rating_count, 1)

    def test_only_the_customer_can_review_and_rating_range(self):
        self.complete()
        self.assertEqual(client_for(self.w.customer2).post("/api/reviews/", {"order": self.order.pk, "rating": 5}, format="json").status_code, 403)
        self.assertEqual(client_for(self.w.customer).post("/api/reviews/", {"order": self.order.pk, "rating": 6}, format="json").status_code, 400)

    def test_business_owner_cannot_edit_review_but_can_report_it(self):
        self.complete()
        rid = client_for(self.w.customer).post("/api/reviews/", {"order": self.order.pk, "rating": 2}, format="json").data["id"]
        owner = client_for(self.w.owner)
        self.assertEqual(owner.patch(f"/api/reviews/{rid}/", {"rating": 5}, format="json").status_code, 404)
        self.assertEqual(owner.delete(f"/api/reviews/{rid}/").status_code, 405)
        r = owner.post("/api/abuse-reports/", {"target_type": "review", "target_id": rid, "reason": "تعليق مسيء"}, format="json")
        self.assertEqual(r.status_code, 201)
        # Admin hides it -> rating recalculated
        rep = AbuseReport.objects.get()
        r = client_for(self.w.admin).post(f"/api/admin/abuse-reports/{rep.pk}/resolve/", {"decision": "resolved", "hide_content": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.w.business.refresh_from_db()
        self.assertEqual(self.w.business.rating_count, 0)
        self.assertEqual(client_for().get("/api/reviews/", {"business": self.w.business.pk}).data["count"], 0)

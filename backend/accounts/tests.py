from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from core.testutils import PASSWORD, World, client_for


class AuthTests(TestCase):
    def setUp(self):
        self.w = World()
        self.c = APIClient()

    def test_register_login_and_me(self):
        r = self.c.post("/api/auth/register/", {
            "email": "New@Test.test", "password": "Very-Strong-987", "full_name": "مستخدم جديد", "city": self.w.nablus.pk,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIn("access", r.data)
        user = User.objects.get(email="new@test.test")
        self.assertNotEqual(user.password, "Very-Strong-987")  # hashed
        self.assertTrue(user.check_password("Very-Strong-987"))

        r = self.c.post("/api/auth/login/", {"email": "new@test.test", "password": "Very-Strong-987"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])
        r = self.c.get("/api/auth/me/")
        self.assertEqual(r.data["email"], "new@test.test")
        self.assertEqual(r.data["roles"], ["customer"])

    def test_register_rejects_weak_password_and_duplicate_email(self):
        r = self.c.post("/api/auth/register/", {"email": "a@t.test", "password": "12345678", "full_name": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/auth/register/", {"email": "customer@t.test", "password": "Very-Strong-987", "full_name": "x"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_wrong_password_and_suspended_account_cannot_login(self):
        r = self.c.post("/api/auth/login/", {"email": "customer@t.test", "password": "wrong-pass"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.w.customer.is_active = False
        self.w.customer.save()
        r = self.c.post("/api/auth/login/", {"email": "customer@t.test", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_one_account_can_hold_customer_business_and_supplier_roles(self):
        from catalog.models import BusinessProfile

        BusinessProfile.objects.create(owner=self.w.supplier_user, name="مشروع", category=self.w.cat_emb, city=self.w.nablus)
        r = client_for(self.w.supplier_user).get("/api/auth/me/")
        self.assertEqual(set(r.data["roles"]), {"customer", "business", "supplier"})

    def test_addresses_are_private(self):
        r = client_for(self.w.customer2).get("/api/addresses/")
        self.assertEqual(r.data, [])
        r = client_for(self.w.customer2).get(f"/api/addresses/{self.w.address.pk}/")
        self.assertEqual(r.status_code, 404)
        r = client_for(self.w.customer).get("/api/addresses/")
        self.assertEqual(len(r.data), 1)

    def test_admin_endpoints_require_staff(self):
        self.assertEqual(client_for(self.w.customer).get("/api/admin/users/").status_code, 403)
        self.assertEqual(client_for().get("/api/reports/admin/").status_code, 401)
        r = client_for(self.w.admin).post(f"/api/admin/users/{self.w.customer.pk}/set_active/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.w.customer.refresh_from_db()
        self.assertFalse(self.w.customer.is_active)
        from core.models import AuditLog

        self.assertTrue(AuditLog.objects.filter(action="suspend_user").exists())


class SpecificAddressTests(TestCase):
    """Business owners (and customers) can save street-level details and an exact map pin."""

    def setUp(self):
        self.w = World()
        self.c = client_for(self.w.owner)

    def body(self, **kw):
        data = {
            "label": "المشغل", "recipient_name": "أم أحمد", "phone": "0591234567", "city": self.w.nablus.pk,
            "area": self.w.rafidia.pk, "street": "شارع رفيديا", "building": "12", "floor": "3",
            "apartment": "5", "landmark": "مقابل مدرسة البنات", "details": "",
            "latitude": 32.2211234567, "longitude": 35.2544987654,
        }
        data.update(kw)
        return data

    def test_create_with_street_details_and_pin(self):
        r = self.c.post("/api/addresses/", self.body(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["latitude"], 32.221123)  # rounded to 6 decimals (~10 cm)
        self.assertEqual(r.data["longitude"], 35.254499)
        self.assertEqual(r.data["map_url"], "https://www.google.com/maps?q=32.221123,35.254499")
        self.assertIn("شارع رفيديا", r.data["full_text"])
        self.assertIn("بناية 12", r.data["full_text"])
        self.assertIn("أقرب معلم: مقابل مدرسة البنات", r.data["full_text"])
        self.assertIn("شقة/محل 5", r.data["full_text"])
        r = self.c.post("/api/addresses/", self.body(building="عمارة النور", apartment="مشغل 2"), format="json")
        self.assertIn("عمارة النور", r.data["full_text"])
        self.assertNotIn("بناية عمارة", r.data["full_text"])
        self.assertNotIn("شقة/محل مشغل", r.data["full_text"])

    def test_pin_is_optional_but_must_be_complete_and_valid(self):
        r = self.c.post("/api/addresses/", self.body(latitude=None, longitude=None), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data["map_url"])
        self.assertEqual(self.c.post("/api/addresses/", self.body(longitude=None), format="json").status_code, 400)
        self.assertEqual(self.c.post("/api/addresses/", self.body(latitude=95), format="json").status_code, 400)
        self.assertEqual(self.c.post("/api/addresses/", self.body(latitude=0, longitude=0), format="json").status_code, 400)

    def test_needs_street_landmark_or_details(self):
        r = self.c.post("/api/addresses/", self.body(street="", landmark="", details=""), format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/addresses/", self.body(street="", details="", landmark="خلف المسجد الكبير"), format="json")
        self.assertEqual(r.status_code, 201)

    def test_edit_address_and_remove_pin(self):
        aid = self.c.post("/api/addresses/", self.body(), format="json").data["id"]
        r = self.c.patch(f"/api/addresses/{aid}/", {"floor": "4", "latitude": None, "longitude": None}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["floor"], "4")
        self.assertIsNone(r.data["map_url"])

    def test_purchase_order_snapshot_carries_pin_privately(self):
        from orders import service

        aid = self.c.post("/api/addresses/", self.body(), format="json").data["id"]
        order = service.create_purchase_order(
            self.w.owner, items=[{"material_id": self.w.fabric.pk, "quantity": "2"}], fulfillment="delivery", address_id=aid,
        )
        r = client_for(self.w.supplier_user).get(f"/api/purchase-orders/{order.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["delivery_map_url"], "https://www.google.com/maps?q=32.221123,35.254499")
        self.assertEqual(r.data["delivery_landmark"], "مقابل مدرسة البنات")
        self.assertIn("الطابق 3", r.data["delivery_address"])
        # Editing the saved address later does not change the order
        self.c.patch(f"/api/addresses/{aid}/", {"street": "شارع آخر"}, format="json")
        r = client_for(self.w.supplier_user).get(f"/api/purchase-orders/{order.pk}/")
        self.assertIn("شارع رفيديا", r.data["delivery_address"])
        # Nobody else can see it
        self.assertEqual(client_for(self.w.customer).get(f"/api/purchase-orders/{order.pk}/").status_code, 404)
        self.assertEqual(client_for(self.w.customer).get(f"/api/addresses/{aid}/").status_code, 404)
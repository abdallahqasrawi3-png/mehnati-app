from decimal import Decimal

from django.test import TestCase

from catalog.models import Offer
from core.testutils import World, client_for, png_upload


class OfferManagementTests(TestCase):
    def setUp(self):
        self.w = World()

    def test_owner_creates_offer_with_initial_stock_and_image(self):
        c = client_for(self.w.owner)
        r = c.post("/api/my/offers/", {
            "title": "شال مطرز", "category": self.w.cat_emb.pk, "offer_type": "ready", "price": "120.00",
            "preparation_days": 2, "initial_stock": 5, "unit_cost": "50",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        offer = Offer.objects.get(pk=r.data["id"])
        self.assertEqual(offer.stock_quantity, 5)
        self.assertEqual(offer.movements.count(), 1)
        r = c.post(f"/api/my/offers/{offer.pk}/images/", {"image": png_upload()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)

    def test_rejects_non_image_upload(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad = SimpleUploadedFile("evil.png", b"#!/bin/sh\necho hacked", content_type="image/png")
        r = client_for(self.w.owner).post(f"/api/my/offers/{self.w.ready.pk}/images/", {"image": bad}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_user_without_business_cannot_create_offers(self):
        r = client_for(self.w.customer).post("/api/my/offers/", {"title": "x"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_owner_cannot_touch_other_owners_offer(self):
        c = client_for(self.w.owner2)
        self.assertEqual(c.patch(f"/api/my/offers/{self.w.ready.pk}/", {"price": "1"}, format="json").status_code, 404)
        self.assertEqual(c.delete(f"/api/my/offers/{self.w.ready.pk}/").status_code, 404)
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.price, Decimal("80"))

    def test_delete_is_soft_and_hides_offer(self):
        c = client_for(self.w.owner)
        self.assertEqual(c.delete(f"/api/my/offers/{self.w.custom.pk}/").status_code, 204)
        self.assertTrue(Offer.objects.filter(pk=self.w.custom.pk, is_deleted=True).exists())
        self.assertEqual(client_for().get(f"/api/offers/{self.w.custom.pk}/").status_code, 404)

    def test_unit_cost_is_never_public(self):
        r = client_for().get(f"/api/offers/{self.w.ready.pk}/")
        self.assertNotIn("unit_cost", r.data)
        self.assertNotIn("stock_quantity", r.data)

    def test_contact_details_need_consent(self):
        r = client_for().get(f"/api/businesses/{self.w.business.pk}/")
        self.assertIsNone(r.data["public_phone"])
        self.w.business.contact_consent = True
        self.w.business.save()
        r = client_for().get(f"/api/businesses/{self.w.business.pk}/")
        self.assertEqual(r.data["public_phone"], "0591111111")
        self.assertNotIn("owner", r.data)

    def test_category_admin_only(self):
        self.assertEqual(client_for(self.w.owner).post("/api/categories/", {"name": "جديد", "kind": "offer"}).status_code, 403)
        self.assertEqual(client_for(self.w.admin).post("/api/categories/", {"name": "جديد", "kind": "offer"}).status_code, 201)


class SearchTests(TestCase):
    def setUp(self):
        self.w = World()
        self.c = client_for()  # visitors can search without signing in

    def ids(self, params):
        r = self.c.get("/api/offers/", params)
        self.assertEqual(r.status_code, 200)
        return {o["id"] for o in r.data["results"]}

    def test_keyword_with_arabic_variants(self):
        self.assertEqual(self.ids({"q": "مطرزه"}), {self.w.ready.pk, self.w.custom.pk})  # ة/ه tolerant

    def test_filters(self):
        self.assertEqual(self.ids({"max_price": "100"}), {self.w.ready.pk, self.w.food.pk})
        self.assertEqual(self.ids({"city": self.w.ramallah.pk}), {self.w.food.pk})
        self.assertEqual(self.ids({"offer_type": "ready"}), {self.w.ready.pk})
        self.assertEqual(self.ids({"max_prep_days": 2}), {self.w.ready.pk, self.w.food.pk})
        self.assertEqual(self.ids({"category": self.w.cat_food.pk}), {self.w.food.pk})
        self.assertEqual(self.ids({"area": self.w.rafidia.pk}), {self.w.ready.pk, self.w.custom.pk})

    def test_available_filter_excludes_sold_out(self):
        self.w.ready.reserved_quantity = 3
        self.w.ready.save()
        self.assertNotIn(self.w.ready.pk, self.ids({"available": "1"}))

    def test_rating_filter_and_ordering(self):
        self.w.business2.rating_avg = Decimal("4.5")
        self.w.business2.save()
        self.assertEqual(self.ids({"min_rating": "4"}), {self.w.food.pk})
        r = self.c.get("/api/offers/", {"ordering": "price"})
        prices = [Decimal(o["price"]) for o in r.data["results"]]
        self.assertEqual(prices, sorted(prices))

    def test_compare_shows_units(self):
        self.w.food.price_unit = "للصينية"
        self.w.food.save()
        r = self.c.get("/api/offers/compare/", {"ids": f"{self.w.ready.pk},{self.w.food.pk}"})
        self.assertEqual(len(r.data["offers"]), 2)
        self.assertFalse(r.data["same_unit"])

    def test_material_search_and_compare_by_unit(self):
        r = self.c.get("/api/materials/", {"q": "كتان", "max_delivery_days": 3})
        self.assertEqual([m["id"] for m in r.data["results"]], [self.w.fabric.pk])
        self.assertEqual(r.data["results"][0]["unit_display"], "متر")

from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings

from ai_assistant import parser
from catalog.models import Category
from core.models import City
from core.testutils import World, client_for


class ParserTests(TestCase):
    def setUp(self):
        self.w = World()
        self.cats = list(Category.objects.filter(kind="offer").values_list("id", "name"))
        self.cities = list(City.objects.values_list("id", "name"))

    def test_customer_example_from_requirements(self):
        c = parser.parse("أريد هدية مطرزة بأقل من 100 شيكل وتكون جاهزة خلال أربعة أيام ويفضل أن تكون من نابلس",
                         "offers", self.cats, self.cities)
        self.assertEqual(c["max_price"], 100)
        self.assertEqual(c["max_days"], 4)
        self.assertEqual(c["city_id"], self.w.nablus.pk)
        self.assertTrue(c["city_is_preference"])
        self.assertIn(self.w.cat_emb.pk, c["category_ids"])

    def test_business_owner_material_example(self):
        mats = list(Category.objects.filter(kind="material").values_list("id", "name"))
        c = parser.parse("أريد قماشًا مناسبًا للتطريز بسعر جيد ويصل إلى منطقتي خلال يومين", "materials", mats,
                         self.cities, user_city=self.w.nablus.pk)
        self.assertEqual(c["max_days"], 2)
        self.assertTrue(c["prefer_cheap"])
        self.assertTrue(c["needs_delivery"])
        self.assertIn(self.w.cat_fabric.pk, c["category_ids"])
        self.assertEqual(c["city_id"], self.w.nablus.pk)

    def test_strict_city_without_preference_word(self):
        c = parser.parse("معمول من رام الله", "offers", self.cats, self.cities)
        self.assertFalse(c["city_is_preference"])


@override_settings(ANTHROPIC_API_KEY="")
class SmartSearchWithoutKeyTests(TestCase):
    """Core functions work with no AI key: the built-in parser is used."""

    def setUp(self):
        self.w = World()

    def test_status_reports_no_external_ai(self):
        r = client_for().get("/api/ai/status/")
        self.assertFalse(r.data["external_ai_enabled"])

    def test_results_come_from_database_with_reasons(self):
        r = client_for().post("/api/ai/search/", {
            "text": "أريد هدية مطرزة بأقل من 100 شيكل وتكون جاهزة خلال أربعة أيام ويفضل أن تكون من نابلس"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["source"], "rules")
        full = [x for x in r.data["results"] if x["match"] == "full"]
        self.assertEqual([x["item"]["id"] for x in full], [self.w.ready.pk])
        self.assertEqual(Decimal(full[0]["item"]["price"]), Decimal("80"))  # real DB price
        self.assertTrue(full[0]["reasons"])

    def test_near_matches_are_labelled_with_unmet_conditions(self):
        r = client_for().post("/api/ai/search/", {"text": "ثوب مطرز بأقل من 100 شيكل"}, format="json")
        near = [x for x in r.data["results"] if x["match"] == "near"]
        self.assertTrue(near)
        self.assertTrue(any("أعلى من الحد" in u for x in near for u in x["unmet"]))

    def test_marketing_draft_uses_template_and_real_facts(self):
        r = client_for(self.w.owner).post("/api/ai/marketing-draft/", {"offer_id": self.w.ready.pk}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["source"], "template")
        self.assertIn("80", r.data["draft"])
        # Draft is not saved automatically
        self.w.ready.refresh_from_db()
        self.assertEqual(self.w.ready.description, "")

    def test_marketing_draft_only_for_own_offers(self):
        r = client_for(self.w.owner2).post("/api/ai/marketing-draft/", {"offer_id": self.w.ready.pk}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_business_summary_numbers_from_code(self):
        r = client_for(self.w.owner).get("/api/ai/business-summary/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["source"], "template")
        self.assertIn("report", r.data)


@override_settings(ANTHROPIC_API_KEY="test-key")
class SmartSearchProviderFailureTests(TestCase):
    """When the AI service is down, search still works using the built-in parser."""

    def setUp(self):
        self.w = World()

    def test_outage_falls_back_to_rules(self):
        with mock.patch("ai_assistant.provider._call", return_value=None):
            r = client_for().post("/api/ai/search/", {"text": "طارة مطرزة"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["source"], "rules")

    def test_ai_output_is_validated_against_real_data(self):
        fake = '{"keywords": [], "category_names": ["تصنيف مخترع", "تطريز"], "city_name": "مدينة وهمية", "city_is_preference": true, "max_price": 100, "min_price": null, "max_days": null, "offer_type": null, "min_rating": null, "needs_delivery": false, "prefer_cheap": false}'
        with mock.patch("ai_assistant.provider._call", return_value=fake):
            r = client_for().post("/api/ai/search/", {"text": "اي شي"}, format="json")
        self.assertEqual(r.data["source"], "ai")
        self.assertEqual(r.data["criteria"]["mandatory"], ["السعر لا يزيد عن 100 ₪", "التصنيف: تطريز"])
        ids = {x["item"]["id"] for x in r.data["results"] if x["match"] == "full"}
        self.assertEqual(ids, {self.w.ready.pk})

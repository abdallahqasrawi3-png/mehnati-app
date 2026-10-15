from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase, TestCase, override_settings

from core.models import ContactMessage
from core.testutils import World, client_for
from mehnaty.settings import database_from_url

URL = "postgresql://user:secret@ep-test-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


class DatabaseUrlTests(SimpleTestCase):
    """DATABASE_URL pasted into hosting dashboards in the forms people actually use."""

    def check(self, raw):
        db = database_from_url(raw)
        self.assertEqual(db["HOST"], "ep-test-pooler.eu-central-1.aws.neon.tech")
        self.assertEqual(db["NAME"], "neondb")
        self.assertEqual(db["USER"], "user")
        self.assertEqual(db["PASSWORD"], "secret")
        self.assertEqual(db["OPTIONS"], {"sslmode": "require", "channel_binding": "require"})
        self.assertTrue(db["DISABLE_SERVER_SIDE_CURSORS"])  # pooled endpoint

    def test_plain_link(self):
        self.check(URL)

    def test_common_paste_mistakes(self):
        for raw in (f"DATABASE_URL={URL}", f"'{URL}'", f'"{URL}"', f"psql '{URL}'", f"  {URL}  ",
                    f"DATABASE_URL='{URL}'"):
            with self.subTest(raw=raw[:20]):
                self.check(raw)

    def test_invalid_value_error_does_not_leak_password(self):
        with self.assertRaises(RuntimeError) as ctx:
            database_from_url("mysql://user:secret@host/db")
        self.assertNotIn("secret", str(ctx.exception))
        self.assertIn("'mysql'", str(ctx.exception))


@override_settings(ADMIN_WHATSAPP="972569228977")
class ContactAdminTests(TestCase):
    def setUp(self):
        self.w = World()

    def body(self, **kw):
        return {"name": "سارة", "phone": "0591234567", "kind": "order", "order_ref": "15",
                "message": "الطلب وصل متأخرًا جدًا والمحل لا يرد.", **kw}

    def test_visitor_can_report_and_gets_whatsapp_link(self):
        r = client_for().post("/api/contact-admin/", self.body(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        msg = ContactMessage.objects.get(pk=r.data["id"])
        self.assertIsNone(msg.user)
        url = urlsplit(r.data["whatsapp_url"])
        self.assertEqual((url.netloc, url.path), ("wa.me", "/972569228977"))
        text = parse_qs(url.query)["text"][0]
        for part in (f"#{msg.pk}", "شكوى على طلب", "سارة", "0591234567", "رقم الطلب: 15", "متأخرًا"):
            self.assertIn(part, text)

    def test_signed_in_user_is_linked_and_email_included(self):
        r = client_for(self.w.customer).post("/api/contact-admin/", self.body(phone="", order_ref=""), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(ContactMessage.objects.get(pk=r.data["id"]).user, self.w.customer)
        text = parse_qs(urlsplit(r.data["whatsapp_url"]).query)["text"][0]
        self.assertIn(self.w.customer.email, text)
        self.assertNotIn("رقم الطلب", text)

    def test_validation(self):
        c = client_for()
        self.assertEqual(c.post("/api/contact-admin/", self.body(message="قصير"), format="json").status_code, 400)
        self.assertEqual(c.post("/api/contact-admin/", self.body(name=" "), format="json").status_code, 400)
        self.assertEqual(c.post("/api/contact-admin/", self.body(kind="spam"), format="json").status_code, 400)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_only_admins_list_and_resolve(self):
        mid = client_for().post("/api/contact-admin/", self.body(), format="json").data["id"]
        self.assertEqual(client_for(self.w.customer).get("/api/admin/contact-messages/").status_code, 403)
        admin = client_for(self.w.admin)
        r = admin.get("/api/admin/contact-messages/", {"status": "open"})
        self.assertEqual(r.data["count"], 1)
        r = admin.post(f"/api/admin/contact-messages/{mid}/resolve/", {"note": "تم التواصل"}, format="json")
        self.assertEqual(r.data["status"], "resolved")
        self.assertEqual(admin.get("/api/admin/contact-messages/", {"status": "open"}).data["count"], 0)

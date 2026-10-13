from django.test import SimpleTestCase

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

"""Shared helpers for tests."""
import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import Address, User
from catalog.models import BusinessProfile, Category, Offer
from core.models import Area, City
from inventory import service as stock
from suppliers.models import Material, SupplierProfile

PASSWORD = "Strong-Pass-123"


def png_upload(name="x.png"):
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), (200, 10, 10)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class World:
    """A small realistic dataset built fresh for each test."""

    def __init__(self):
        self.nablus = City.objects.create(name="نابلس")
        self.ramallah = City.objects.create(name="رام الله")
        self.rafidia = Area.objects.create(city=self.nablus, name="رفيديا")
        self.cat_emb = Category.objects.create(name="تطريز", kind=Category.Kind.OFFER)
        self.cat_food = Category.objects.create(name="مأكولات منزلية", kind=Category.Kind.OFFER)
        self.cat_gift = Category.objects.create(name="هدايا", kind=Category.Kind.OFFER)
        self.cat_fabric = Category.objects.create(name="أقمشة", kind=Category.Kind.MATERIAL)

        self.customer = self.make_user("customer@t.test", "سارة")
        self.customer2 = self.make_user("customer2@t.test", "محمد")
        self.owner = self.make_user("owner@t.test", "أم أحمد")
        self.owner2 = self.make_user("owner2@t.test", "سلمى")
        self.supplier_user = self.make_user("supplier@t.test", "المورد")
        self.admin = self.make_user("admin@t.test", "المدير")
        self.admin.is_staff = True
        self.admin.save()

        self.address = Address.objects.create(
            user=self.customer, recipient_name="سارة", phone="0590000000", city=self.nablus, details="شارع 1"
        )
        self.business = BusinessProfile.objects.create(
            owner=self.owner, name="مطرزات", category=self.cat_emb, city=self.nablus, area=self.rafidia,
            delivery_available=True, public_phone="0591111111", contact_consent=False,
        )
        self.business2 = BusinessProfile.objects.create(
            owner=self.owner2, name="مطبخ سلمى", category=self.cat_food, city=self.ramallah, delivery_available=False,
        )
        self.ready = Offer.objects.create(
            business=self.business, title="طارة مطرزة هدية", category=self.cat_emb, offer_type="ready",
            price=Decimal("80"), unit_cost=Decimal("30"), preparation_days=1, low_stock_threshold=1,
        )
        stock.adjust(self.ready, 3, actor=self.owner)
        self.ready.refresh_from_db()
        self.custom = Offer.objects.create(
            business=self.business, title="ثوب مطرز حسب الطلب", category=self.cat_emb, offer_type="made_to_order",
            price=Decimal("400"), preparation_days=20,
        )
        self.food = Offer.objects.create(
            business=self.business2, title="معمول بالتمر", category=self.cat_food, offer_type="made_to_order",
            price=Decimal("60"), unit_cost=Decimal("35"), preparation_days=2,
        )
        self.supplier = SupplierProfile.objects.create(
            owner=self.supplier_user, name="الإبرة الذهبية", city=self.nablus, delivery_available=True,
            delivery_cost=Decimal("15"), delivery_days=2,
        )
        self.fabric = Material.objects.create(
            supplier=self.supplier, title="قماش كتان للتطريز", category=self.cat_fabric, unit="meter",
            price=Decimal("18"), min_order_quantity=Decimal("2"), low_stock_threshold=Decimal("5"),
        )
        stock.adjust(self.fabric, Decimal("20"), actor=self.supplier_user)
        self.fabric.refresh_from_db()

    @staticmethod
    def make_user(email, name):
        return User.objects.create_user(email=email, password=PASSWORD, full_name=name)


def client_for(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user)
    return c

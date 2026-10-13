"""OPTIONAL DEMO DATA - for trying the app only.

Businesses and suppliers come from the owner's table of Jenin home businesses (core/demo_data.py).
Accounts are demo accounts: emails end with @demo.mehnaty.test and names carry «[تجريبي]».
Products and prices are illustrative (the table has none). No reviews or ratings are generated.
A few orders are created through the normal order rules so stock and reports are consistent.

Demo password for every demo account: DEMO_PASSWORD below.
Remove all demo data with:  python manage.py seed_demo --remove
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image

from accounts.models import Address, User
from catalog.models import BusinessProfile, Category, Offer, OfferImage
from core.demo_data import BUSINESSES, JENIN_AREAS, SUPPLIERS
from core.models import Area, City
from inventory import service as stock
from orders import service as orders
from orders.models import SalesOrder
from reports.models import Expense
from reviews.models import Review
from suppliers.models import Material, MaterialImage, SupplierProfile

DEMO_DOMAIN = "@demo.mehnaty.test"
DEMO_PASSWORD = "Mehnaty-Demo-2026"
TAG = " [تجريبي]"
PRICE_NOTE = " (سعر تجريبي للعرض)"

ASSETS = settings.BASE_DIR.parent  # project folder that holds logo.jpeg and background.jpeg
CROPS = {
    "hoop": ("background.jpeg", (290, 330, 700, 730)),
    "food_frame": ("background.jpeg", (605, 65, 865, 350)),
    "tree": ("background.jpeg", (795, 315, 1045, 565)),
    "threads": ("background.jpeg", (790, 580, 1080, 790)),
    "spools": ("background.jpeg", (110, 640, 450, 850)),
    "fabric": ("background.jpeg", (560, 480, 860, 760)),
    "flowers_hoop": ("logo.jpeg", (120, 140, 430, 470)),
    "cupcake": ("logo.jpeg", (530, 790, 660, 910)),
    "pot": ("logo.jpeg", (1290, 620, 1450, 800)),
    "sewing": ("logo.jpeg", (700, 720, 1000, 960)),
    "embroidered_cloth": ("logo.jpeg", (960, 700, 1180, 950)),
    "food_plate": ("logo.jpeg", (1500, 70, 1735, 325)),
    "rose_hoop": ("logo.jpeg", (1530, 380, 1810, 700)),
}


def demo_image(key):
    name, box = CROPS[key]
    path = ASSETS / name
    try:
        img = Image.open(path).convert("RGB").crop(box)
    except (FileNotFoundError, OSError):
        img = Image.new("RGB", (400, 400), (31, 92, 63))
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return ContentFile(buf.getvalue(), name=f"demo_{key}.jpg")


class Command(BaseCommand):
    help = "Create (or --remove) clearly-marked demo data."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true")

    def handle(self, *args, **opts):
        if opts["remove"]:
            self.remove()
            return
        if User.objects.filter(email__endswith=DEMO_DOMAIN).exists():
            self.stdout.write("Demo data already exists (use --remove first to recreate).")
            return
        call_command("seed_reference")
        with transaction.atomic():
            self.create()
        self.stdout.write(self.style.SUCCESS(
            "Demo data created. Demo accounts use the password defined in seed_demo.py (DEMO_PASSWORD)."
        ))

    def remove(self):
        users = User.objects.filter(email__endswith=DEMO_DOMAIN)
        from inventory.models import InventoryMovement
        from notifications.models import Notification
        from orders.models import OrderStatusLog, PurchaseOrder
        from shipping.models import Shipment

        with transaction.atomic():
            Shipment.objects.filter(sender__in=users).delete()
            Review.objects.filter(customer__in=users).delete()
            InventoryMovement.objects.filter(actor__in=users).delete()
            OrderStatusLog.objects.filter(actor__in=users).delete()
            SalesOrder.objects.filter(customer__in=users).delete()
            SalesOrder.objects.filter(business__owner__in=users).delete()
            PurchaseOrder.objects.filter(buyer__in=users).delete()
            PurchaseOrder.objects.filter(supplier__owner__in=users).delete()
            Notification.objects.filter(user__in=users).delete()
            n = users.count()
            users.delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {n} demo accounts and their data."))

    def user(self, local, name, city, staff=False):
        u = User.objects.create_user(
            email=f"{local}{DEMO_DOMAIN}", password=DEMO_PASSWORD, full_name=name + TAG, city=city,
        )
        if staff:
            u.is_staff = True
            u.is_superuser = True
            u.save()
        return u

    def create(self):
        jenin = City.objects.get(name="جنين")
        areas = {a.name: a for a in Area.objects.filter(city=jenin, name__in=JENIN_AREAS)}
        cat = {(c.name, c.kind): c for c in Category.objects.all()}
        offer_cat = lambda name: cat[(name, Category.Kind.OFFER)]
        material_cat = lambda name: cat[(name, Category.Kind.MATERIAL)]

        # ---- Demo customers and platform admin
        self.user("admin", "مدير المنصة", jenin, staff=True)
        customer = self.user("customer", "سارة أحمد", jenin)
        customer2 = self.user("customer2", "محمد خالد", jenin)
        Address.objects.create(user=customer, label="المنزل", recipient_name="سارة أحمد", phone="0590000000",
                               city=jenin, area=areas["المدينة"], street="عنوان تجريبي", details="بناية تجريبية")
        Address.objects.create(user=customer2, label="المنزل", recipient_name="محمد خالد", phone="0590000001",
                               city=jenin, area=areas["برقين"], landmark="عنوان تجريبي")

        # ---- Home businesses from the table
        R, M, S = Offer.OfferType.READY, Offer.OfferType.MADE_TO_ORDER, Offer.OfferType.SERVICE
        businesses, offers_by_title = {}, {}
        for i, b in enumerate(BUSINESSES, start=1):
            owner = self.user(f"owner{i:02d}", b["owner"], jenin)
            area = areas.get(b["area"]) if b["area"] else None
            profile = BusinessProfile.objects.create(
                owner=owner, name=b["name"], category=offer_cat(b["category"]), city=jenin, area=area,
                description=b["about"], contact_consent=False, pickup_available=True, delivery_available=True,
            )
            if b["address"]:
                Address.objects.create(
                    user=owner, label="المشروع", recipient_name=b["owner"], phone="0590000000", city=jenin, area=area,
                    street=b["address"].get("street", ""), landmark=b["address"].get("landmark", ""),
                )
            for title, category, otype, price, unit, prep, qty, img, desc in b["offers"]:
                o = Offer.objects.create(
                    business=profile, title=title, category=offer_cat(category), offer_type=otype,
                    price=Decimal(price), price_unit=unit, preparation_days=prep, description=desc + PRICE_NOTE,
                    low_stock_threshold=2 if otype == R else 0,
                )
                OfferImage.objects.create(offer=o, image=demo_image(img))
                if qty:
                    stock.adjust(o, qty, actor=owner, note="كمية تجريبية")
                offers_by_title[title] = o
            businesses[b["name"]] = profile

        # ---- Sales channels from the table, as suppliers
        suppliers, materials_by_title = {}, {}
        for s in SUPPLIERS:
            owner = self.user(f"supplier-{s['key']}", s["name"], jenin)
            sp = SupplierProfile.objects.create(
                owner=owner, name=s["name"], description=s["about"], city=jenin, area=areas.get(s["area"]),
                contact_consent=False, pickup_available=True, delivery_available=True,
                delivery_cost=Decimal("10"), delivery_days=1,
            )
            for title, category, unit, price, qty, minq, img, specs in s["materials"]:
                m = Material.objects.create(
                    supplier=sp, title=title, category=material_cat(category), unit=unit, price=Decimal(price),
                    min_order_quantity=Decimal(minq), specifications=specs, preparation_days=1,
                    description="سعر تجريبي للعرض", low_stock_threshold=Decimal("5"),
                )
                MaterialImage.objects.create(material=m, image=demo_image(img))
                stock.adjust(m, Decimal(qty), actor=owner, note="كمية تجريبية")
                materials_by_title[title] = m
            suppliers[s["key"]] = sp

        # ---- A few orders through the normal rules (no reviews are generated)
        now = timezone.now()
        emy = businesses["Emy Chocolate - ايمي شوكليت"]
        o = orders.create_sales_order(customer, items=[{"offer_id": offers_by_title["علبة شوكولاتة مشكلة"].pk, "quantity": 2}],
                                      fulfillment="pickup")
        for st in ["accepted", "preparing", "ready", "completed"]:
            orders.transition_sales_order(emy.owner, o.pk, st)
        SalesOrder.objects.filter(pk=o.pk).update(completed_at=now - timedelta(days=2))

        bongbong = businesses["BongBong - حلويات حوري"]
        o2 = orders.create_sales_order(customer2, items=[{"offer_id": offers_by_title["كاسات تشيز كيك"].pk, "quantity": 4}],
                                       fulfillment="delivery", address_id=customer2.addresses.first().pk)
        orders.set_delivery_terms(bongbong.owner, SalesOrder.objects.get(pk=o2.pk), delivery_fee=Decimal("10"),
                                  delivery_payer="buyer", delivery_fee_is_final=True)
        for st in ["accepted", "preparing", "ready", "in_transit", "completed"]:
            orders.transition_sales_order(bongbong.owner, o2.pk, st)

        orders.create_sales_order(customer, items=[{"offer_id": offers_by_title["مسخن بلدي"].pk, "quantity": 1}],
                                  fulfillment="pickup", notes="للاستلام مساءً إن أمكن")
        Expense.objects.create(business=emy, date=timezone.localdate(), category="packaging", amount=Decimal("15"),
                               note="علب تغليف (تجريبي)")

        # A home business buys raw materials from a supplier named in the table
        po = orders.create_purchase_order(
            emy.owner, items=[{"material_id": materials_by_title["شوكولاتة طبخ"].pk, "quantity": "2"}], fulfillment="pickup",
        )
        orders.transition_purchase_order(suppliers["karim"].owner, po.pk, "accepted")

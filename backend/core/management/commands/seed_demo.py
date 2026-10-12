"""OPTIONAL DEMO DATA - for trying the app only. Clearly marked «[تجريبي]».

Creates demo accounts (emails end with @demo.mehnaty.test), businesses, offers,
a supplier with materials, and a few real orders created through the normal
order rules (so stock, reviews and reports are consistent).

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
from core.models import Area, City
from inventory import service as stock
from orders import service as orders
from orders.models import SalesOrder
from reports.models import Expense
from reviews.models import Review, refresh_business_rating
from suppliers.models import Material, MaterialImage, SupplierProfile

DEMO_DOMAIN = "@demo.mehnaty.test"
DEMO_PASSWORD = "Mehnaty-Demo-2026"
TAG = " [تجريبي]"

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
            f"Demo data created. Demo accounts use the password defined in seed_demo.py (DEMO_PASSWORD)."
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
            email=f"{local}{DEMO_DOMAIN}", password=DEMO_PASSWORD, full_name=name + TAG,
            phone="0590000000", city=city,
        )
        if staff:
            u.is_staff = True
            u.is_superuser = True
            u.save()
        return u

    def create(self):
        city = {c.name: c for c in City.objects.all()}
        cat = {c.name: c for c in Category.objects.all()}
        area = lambda c, n: Area.objects.filter(city=city[c], name=n).first()

        self.user("admin", "مدير المنصة", city["نابلس"], staff=True)
        customer = self.user("customer", "سارة أحمد", city["نابلس"])
        customer2 = self.user("customer2", "محمد خالد", city["رام الله"])
        Address.objects.create(user=customer, label="المنزل", recipient_name="سارة أحمد", phone="0590000000",
                               city=city["نابلس"], area=area("نابلس", "رفيديا"), details="شارع تجريبي، بناية 1")
        Address.objects.create(user=customer2, label="المنزل", recipient_name="محمد خالد", phone="0590000001",
                               city=city["رام الله"], area=area("رام الله", "البيرة"), details="عنوان تجريبي")

        # ---- Home businesses
        o1 = self.user("embroidery", "أم أحمد", city["نابلس"])
        # Business owner's workshop address with street-level details and a demo map pin
        Address.objects.create(
            user=o1, label="المشغل", recipient_name="أم أحمد", phone="0590000010", city=city["نابلس"],
            area=area("نابلس", "المخفية"), street="شارع المخفية الرئيسي (تجريبي)", building="7", floor="الأرضي",
            apartment="مشغل 2", landmark="بجانب مخبز تجريبي", details="الباب الأخضر، الاستلام 9 - 4",
            latitude=Decimal("32.227500"), longitude=Decimal("35.250000"),
        )
        b1 = BusinessProfile.objects.create(
            owner=o1, name="مطرزات أم أحمد" + TAG, category=cat["تطريز"], city=city["نابلس"], area=area("نابلس", "المخفية"),
            description="تطريز فلسطيني يدوي بخيوط عالية الجودة: أثواب، شالات، ولوحات مطرزة كهدايا.",
            public_phone="0590000010", public_whatsapp="0590000010", contact_consent=True,
            working_hours="السبت - الخميس، 9 صباحًا - 6 مساءً", pickup_available=True, delivery_available=True,
        )
        o2 = self.user("kitchen", "سلمى", city["رام الله"])
        b2 = BusinessProfile.objects.create(
            owner=o2, name="مطبخ سلمى" + TAG, category=cat["مأكولات منزلية"], city=city["رام الله"],
            area=area("رام الله", "الطيرة"), description="مأكولات وحلويات منزلية طازجة حسب الطلب.",
            public_phone="0590000020", contact_consent=True, working_hours="يوميًا 10 صباحًا - 8 مساءً",
            pickup_available=True, delivery_available=True,
        )
        o3 = self.user("art", "ليان", city["الخليل"])
        b3 = BusinessProfile.objects.create(
            owner=o3, name="مرسم ليان" + TAG, category=cat["رسم"], city=city["الخليل"],
            description="لوحات مرسومة يدويًا وأعمال فخار ملوّنة.", contact_consent=False,
            working_hours="بالتنسيق المسبق", pickup_available=True, delivery_available=False,
        )

        def offer(b, title, category, otype, price, img, stock_qty=0, cost=None, prep=0, unit="للقطعة", desc="", threshold=0, duration=""):
            o = Offer.objects.create(
                business=b, title=title, category=cat[category], offer_type=otype, price=Decimal(price),
                unit_cost=Decimal(cost) if cost else None, preparation_days=prep, price_unit=unit,
                description=desc, low_stock_threshold=threshold, service_duration=duration,
            )
            OfferImage.objects.create(offer=o, image=demo_image(img))
            if stock_qty:
                stock.adjust(o, stock_qty, actor=b.owner, note="كمية تجريبية")
            return o

        R, M, S = Offer.OfferType.READY, Offer.OfferType.MADE_TO_ORDER, Offer.OfferType.SERVICE
        f1 = offer(b1, "طارة مطرزة بالورود - هدية", "تطريز", R, "85", "flowers_hoop", 6, "35", 1,
                   desc="لوحة تطريز يدوي داخل طارة خشبية، مناسبة كهدية.", threshold=2)
        offer(b1, "شال مطرز بنقوش فلسطينية", "تطريز", R, "120", "embroidered_cloth", 4, "60", 2,
              desc="شال قطني مطرز يدويًا بنقشة تقليدية.", threshold=1)
        offer(b1, "ثوب فلسطيني مطرز حسب المقاس", "تطريز", M, "450", "sewing", 0, "220", 21,
              desc="تفصيل وتطريز ثوب كامل حسب المقاس واللون المطلوب.")
        offer(b1, "لوحة شجرة الصفصاف المطرزة", "هدايا", R, "95", "tree", 3, None, 3,
              desc="لوحة تطريز بخيوط زيتية داخل إطار دائري.")
        offer(b1, "ورشة تعليم تطريز للمبتدئين", "تطريز", S, "60", "hoop", 0, None, 2, unit="للجلسة",
              desc="جلسة تعليم تطريز لساعتين مع الأدوات.", duration="ساعتان")
        f2 = offer(b2, "صينية معمول بالتمر", "مأكولات منزلية", M, "70", "food_plate", 0, "40", 2, unit="للصينية",
                   desc="معمول منزلي محشو بالتمر، 40 حبة تقريبًا.")
        offer(b2, "كب كيك منزلي (12 حبة)", "مأكولات منزلية", R, "45", "cupcake", 10, "20", 0, unit="للعلبة",
              desc="كب كيك طازج بكريمة الفانيلا.", threshold=3)
        offer(b2, "طبق حلويات للمناسبات", "مأكولات منزلية", M, "150", "food_frame", 0, "90", 3, unit="للطبق")
        offer(b3, "جرة فخار ملوّنة يدويًا", "أعمال يدوية", R, "65", "pot", 5, "25", 0, desc="جرة فخار مزخرفة بألوان التطريز.")
        offer(b3, "رسم بورتريه حسب الطلب", "رسم", M, "200", "rose_hoop", 0, None, 7, desc="رسم بورتريه من صورة.")

        # ---- Supplier
        s_owner = self.user("supplier", "الإبرة الذهبية", city["نابلس"])
        sp = SupplierProfile.objects.create(
            owner=s_owner, name="مستلزمات الإبرة الذهبية" + TAG, city=city["نابلس"], area=area("نابلس", "المدينة"),
            description="أقمشة وخيوط وأدوات تطريز وخياطة بالجملة والمفرق.", public_phone="0590000030",
            contact_consent=True, pickup_available=True, delivery_available=True,
            delivery_cost=Decimal("15"), delivery_days=2,
        )
        s2_owner = self.user("supplier2", "بيت الأقمشة", city["رام الله"])
        sp2 = SupplierProfile.objects.create(
            owner=s2_owner, name="بيت الأقمشة" + TAG, city=city["رام الله"], description="أقمشة متنوعة.",
            pickup_available=True, delivery_available=True, delivery_cost=Decimal("25"), delivery_days=4,
        )

        def material(s, title, category, unit, price, qty, minq, img, specs="", threshold=0):
            m = Material.objects.create(
                supplier=s, title=title, category=cat[category], unit=unit, price=Decimal(price),
                min_order_quantity=Decimal(minq), specifications=specs, low_stock_threshold=Decimal(threshold),
                preparation_days=1,
            )
            MaterialImage.objects.create(material=m, image=demo_image(img))
            stock.adjust(m, Decimal(qty), actor=s.owner, note="كمية تجريبية")
            return m

        U = Material.Unit
        m1 = material(sp, "قماش كتان مناسب للتطريز", "أقمشة", U.METER, "18", "120", "2", "fabric",
                      "كتان طبيعي، عرض 150 سم، 11 غرزة/سم", threshold=20)
        material(sp, "خيوط تطريز قطنية (12 لونًا)", "خيوط", U.PACK, "25", "60", "1", "threads",
                 "قطن مصري 100%، 8 أمتار لكل لون", threshold=10)
        material(sp, "طارة تطريز خشبية 25 سم", "أدوات خياطة وتطريز", U.PIECE, "12", "40", "1", "hoop", "خشب زان")
        material(sp, "بكرات خيوط خياطة", "خيوط", U.PACK, "30", "25", "1", "spools", "10 بكرات، ألوان متنوعة")
        material(sp2, "قماش قطني للتطريز", "أقمشة", U.METER, "14", "200", "5", "fabric", "قطن، عرض 140 سم")

        # ---- Real orders through the normal rules
        now = timezone.now()
        o = orders.create_sales_order(customer, items=[{"offer_id": f1.pk, "quantity": 2}], fulfillment="pickup")
        for st in ["accepted", "preparing", "ready", "completed"]:
            orders.transition_sales_order(o1, o.pk, st)
        SalesOrder.objects.filter(pk=o.pk).update(completed_at=now - timedelta(days=3))
        Review.objects.create(order=o, business=b1, customer=customer, rating=5, comment="تطريز رائع ودقيق، شكرًا!")
        o_b = orders.create_sales_order(customer2, items=[{"offer_id": f1.pk, "quantity": 1}], fulfillment="delivery",
                                        address_id=customer2.addresses.first().pk)
        orders.set_delivery_terms(o1, SalesOrder.objects.get(pk=o_b.pk), delivery_fee=Decimal("20"),
                                  delivery_payer="buyer", delivery_fee_is_final=True)
        for st in ["accepted", "preparing", "ready", "in_transit", "completed"]:
            orders.transition_sales_order(o1, o_b.pk, st)
        Review.objects.create(order=o_b, business=b1, customer=customer2, rating=4, comment="جميل جدًا والتوصيل سريع.")
        refresh_business_rating(b1)

        o2_ = orders.create_sales_order(customer, items=[{"offer_id": f2.pk, "quantity": 1}], fulfillment="pickup",
                                        notes="بدون سكر إضافي إن أمكن")
        orders.transition_sales_order(o2, o2_.pk, "accepted")
        Expense.objects.create(business=b1, date=timezone.localdate(), category="packaging", amount=Decimal("15"),
                               note="علب هدايا (تجريبي)")

        # Purchase order: business owner buys fabric for pickup
        po = orders.create_purchase_order(o1, items=[{"material_id": m1.pk, "quantity": "5"}], fulfillment="pickup")
        orders.transition_purchase_order(s_owner, po.pk, "accepted")

"""Reference data the app needs (cities, areas, categories). Safe to run many times.
Administrators can edit all of it later from the admin panel."""
from django.core.management.base import BaseCommand

from catalog.models import Category
from core.models import Area, City

CITIES = {
    "نابلس": ["المدينة", "رفيديا", "المخفية", "بلاطة", "عسكر"],
    "رام الله": ["المدينة", "البيرة", "الطيرة", "الماصيون"],
    "الخليل": ["المدينة", "عين سارة", "رأس الجورة", "الحرس"],
    "جنين": ["المدينة", "الجابريات", "المخيم", "المنطقة الصناعية", "دوار الزايد", "برقين", "الزبابدة", "رابا"],
    "طولكرم": ["المدينة", "شويكة", "ضاحية ذنابة"],
    "قلقيلية": ["المدينة"],
    "بيت لحم": ["المدينة", "بيت جالا", "بيت ساحور"],
    "أريحا": ["المدينة"],
    "سلفيت": ["المدينة"],
    "طوباس": ["المدينة"],
    "القدس": ["البلدة القديمة", "بيت حنينا", "شعفاط"],
    "غزة": ["الرمال", "الشجاعية", "تل الهوى"],
}

OFFER_CATEGORIES = ["تطريز", "خياطة", "رسم", "أعمال يدوية", "هدايا", "مأكولات منزلية", "تجميل"]
MATERIAL_CATEGORIES = ["أقمشة", "خيوط", "أدوات خياطة وتطريز", "مكونات طعام", "مستلزمات تغليف", "أدوات رسم وتزيين"]


class Command(BaseCommand):
    help = "Create reference cities, areas and categories (idempotent)."

    def handle(self, *args, **opts):
        for cname, areas in CITIES.items():
            city, _ = City.objects.get_or_create(name=cname)
            for a in areas:
                Area.objects.get_or_create(city=city, name=a)
        for i, name in enumerate(OFFER_CATEGORIES):
            Category.objects.get_or_create(name=name, kind=Category.Kind.OFFER, defaults={"sort_order": i})
        for i, name in enumerate(MATERIAL_CATEGORIES):
            Category.objects.get_or_create(name=name, kind=Category.Kind.MATERIAL, defaults={"sort_order": i})
        self.stdout.write(self.style.SUCCESS("Reference data ready."))

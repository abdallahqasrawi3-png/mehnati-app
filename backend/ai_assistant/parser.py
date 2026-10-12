"""Built-in rule-based parser for Arabic search requests (no external service).

Example: «أريد هدية مطرزة بأقل من 100 شيكل وتكون جاهزة خلال أربعة أيام ويفضل أن تكون من نابلس»
 -> max_price=100 (mandatory), max_days=4 (mandatory), category=تطريز (mandatory),
    city=نابلس (preference), keywords=[هدية]
"""
import re

from catalog.search import normalize_ar

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

NUMBER_WORDS = {
    "واحد": 1, "يوم": 1, "اثنين": 2, "اثنان": 2, "يومين": 2, "ثلاث": 3, "ثلاثة": 3, "اربع": 4, "أربع": 4,
    "اربعة": 4, "أربعة": 4, "خمس": 5, "خمسة": 5, "ست": 6, "ستة": 6, "سبع": 7, "سبعة": 7, "ثمان": 8,
    "ثمانية": 8, "تسع": 9, "تسعة": 9, "عشر": 10, "عشرة": 10, "عشرين": 20, "خمسين": 50, "مية": 100,
    "مئة": 100, "مائة": 100, "ميه": 100, "مئتين": 200, "ميتين": 200, "الف": 1000, "ألف": 1000,
}

# Words that signal a preference rather than a strict condition
PREFERENCE_MARKERS = ["يفضل", "يفضّل", "ويفضل", "أفضل", "افضل", "لو أمكن", "إن أمكن", "ان امكن", "إذا أمكن", "حبذا"]

# Synonyms that point to category names (matched against real category names in the DB)
CATEGORY_SYNONYMS = {
    "تطريز": ["مطرز", "مطرزة", "مطرزه", "تطريز", "التطريز", "مطرزات"],
    "خياطة": ["خياطة", "خياطه", "خياط", "تفصيل", "فستان", "ثوب", "تعديل ملابس"],
    "رسم": ["رسم", "لوحة", "لوحه", "رسومات", "بورتريه"],
    "أعمال يدوية": ["يدوي", "يدوية", "صناعة يدوية", "اكسسوار", "إكسسوار", "خرز", "صابون", "شموع"],
    "هدايا": ["هدية", "هديه", "هدايا", "تغليف هدايا"],
    "مأكولات منزلية": ["أكل", "اكل", "طبخ", "مأكولات", "ماكولات", "طعام", "حلويات", "كعك", "معمول", "مقلوبة", "مسخن", "معجنات", "كيك"],
    "تجميل": ["تجميل", "مكياج", "حنة", "حناء", "تسريحة"],
    "أقمشة": ["قماش", "قماشا", "قماشًا", "أقمشة", "اقمشة", "كتان", "قطن"],
    "خيوط": ["خيط", "خيوط", "خيطان", "صوف"],
    "أدوات خياطة وتطريز": ["إبرة", "ابرة", "إبر", "ابر", "طارة", "مقص", "أدوات", "ادوات"],
    "مكونات طعام": ["طحين", "سكر", "سمن", "زيت", "بهارات", "مكونات"],
    "مستلزمات تغليف": ["تغليف", "علب", "أكياس", "اكياس", "شرائط"],
}

STOPWORDS = set(
    """أريد اريد بدي ابغى أبغى أبحث ابحث عن عن على من في الى إلى أن ان تكون يكون و او أو مع لي لو هل
    بأقل باقل أقل اقل من خلال جاهزة جاهز جاهزه يفضل ويفضل شيكل شيقل ₪ سعر بسعر جيد مناسب مناسبة
    منطقتي مدينتي يصل تصل يوصل توصيل أيام ايام يوم يومين اسبوع أسبوع أسبوعين حتى بحدود لا يزيد يتجاوز
    شي شيء حاجة اشي ممكن رخيص رخيصة ارخص أرخص للتطريز للخياطة كون نفسي احتاج أحتاج محتاج""".split()
)


def _to_number(token):
    token = token.translate(AR_DIGITS).replace(",", "")
    try:
        return float(token)
    except ValueError:
        return NUMBER_WORDS.get(token)


def _near_preference(text, start):
    window = text[max(0, start - 30):start]
    return any(m in window for m in PREFERENCE_MARKERS)


def parse(text, target, categories, cities, user_city=None):
    """Return a criteria dict. categories: list of (id, name); cities: list of (id, name)."""
    raw = normalize_ar(text).translate(AR_DIGITS)
    crit = {
        "keywords": [], "category_ids": [], "city_id": None, "city_is_preference": True,
        "max_price": None, "min_price": None, "max_days": None, "offer_type": None,
        "min_rating": None, "needs_delivery": False, "prefer_cheap": False,
    }

    # Price limits
    for m in re.finditer(r"(?:ب?أقل من|ب?اقل من|لا يزيد عن|لا يتجاوز|ما يتجاوز|حتى|بحدود|تحت|أقصى|اقصى)\s*(\d+(?:\.\d+)?|\S+)\s*(شيكل|شيقل|₪)?", raw):
        n = _to_number(m.group(1))
        # Bare words like «حتى يومين» are time, not price: need digits or a currency word
        if n is not None and (m.group(2) or m.group(1)[0].isdigit()):
            crit["max_price"] = n
            break
    m = re.search(r"(?:أكثر من|اكثر من|فوق|لا يقل عن)\s*(\d+(?:\.\d+)?)\s*(?:شيكل|شيقل|₪)", raw)
    if m:
        crit["min_price"] = float(m.group(1))
    if re.search(r"سعر (?:جيد|مناسب|رخيص)|رخيص|أرخص|ارخص|اقتصادي", raw):
        crit["prefer_cheap"] = True

    # Time limits ("خلال أربعة أيام", "خلال يومين", "خلال أسبوع")
    m = re.search(r"(?:خلال|في غضون|بغضون|بمدة|أقصاه|اقصاه)\s*(?:(\S+)\s+)?(يومين|أيام|ايام|يوم|أسبوعين|اسبوعين|أسبوع|اسبوع)", raw)
    if m:
        num_tok, unit = m.group(1), m.group(2)
        if unit == "يومين":
            days = 2
        elif unit in ("أسبوعين", "اسبوعين"):
            days = 14
        elif unit in ("أسبوع", "اسبوع"):
            days = 7 * int(_to_number(num_tok) or 1) if num_tok else 7
        else:
            days = int(_to_number(num_tok) or 1) if num_tok else 1
        crit["max_days"] = days

    # Offer type
    if target == "offers":
        if re.search(r"\bخدمة\b|\bخدمه\b|موعد", raw):
            crit["offer_type"] = "service"
        elif "حسب الطلب" in raw:
            crit["offer_type"] = "made_to_order"

    # Rating
    m = re.search(r"(?:تقييم|نجوم)\s*(?:أعلى من|اعلى من|فوق|لا يقل عن)?\s*(\d(?:\.\d)?)", raw)
    if m:
        crit["min_rating"] = float(m.group(1))
    elif re.search(r"تقييم (?:عالي|ممتاز|مرتفع)|موثوق", raw):
        crit["min_rating"] = 4.0

    # Delivery
    if re.search(r"توصيل|يوصل|يصل|تصل|توصل", raw):
        crit["needs_delivery"] = True

    # City
    for cid, cname in cities:
        idx = raw.find(normalize_ar(cname))
        if idx >= 0:
            crit["city_id"] = cid
            crit["city_is_preference"] = _near_preference(raw, idx)
            break
    if crit["city_id"] is None and user_city and re.search(r"منطقتي|مدينتي|قريب|قريبة|بالقرب", raw):
        crit["city_id"] = user_city
        crit["city_is_preference"] = True

    # Categories (only categories that exist for this target)
    cat_by_name = {normalize_ar(n): cid for cid, n in categories}
    words = re.findall(r"[؀-ۿA-Za-z]+", raw)
    used_words = set()
    matched_terms = []
    for canonical, syns in CATEGORY_SYNONYMS.items():
        cid = cat_by_name.get(normalize_ar(canonical))
        for s in syns:
            if s in raw:
                if cid and cid not in crit["category_ids"]:
                    crit["category_ids"].append(cid)
                used_words.update(s.split())
                if s not in matched_terms and not any(s in t for t in matched_terms):
                    matched_terms.append(s)
                break
    # The words themselves also rank results («هدية» ranks gift items above other embroidery)
    crit["keywords"].extend(matched_terms)
    for cname_norm, cid in cat_by_name.items():
        if cname_norm in raw and cid not in crit["category_ids"]:
            crit["category_ids"].append(cid)
            used_words.update(cname_norm.split())

    # Keywords: remaining meaningful words
    city_words = {normalize_ar(c) for _, c in cities}
    for w in words:
        if w.startswith("و") and len(w) > 3 and (w[1:] in STOPWORDS or w[1:] in NUMBER_WORDS):
            continue  # «وتكون»، «ويكون»: conjunction + filler word
        w2 = w[2:] if w.startswith("ال") and len(w) > 4 else w
        if (w in STOPWORDS or w2 in STOPWORDS or len(w2) < 3 or w in city_words
                or w in NUMBER_WORDS or w in used_words or any(t in w for t in matched_terms)):
            continue
        if w2 not in crit["keywords"]:
            crit["keywords"].append(w2)
    crit["keywords"] = crit["keywords"][:6]
    return crit

"""Turn criteria into real database results with explanations.

Mandatory conditions filter; preferences only affect ranking. When there are
few full matches, the closest records are returned and clearly labelled with
the conditions they do not meet. Nothing is invented: every value shown comes
from the database record.
"""
import re
from decimal import Decimal

from django.db.models import Q

from catalog.models import Category, Offer
from catalog.search import ar_regex, keyword_q, public_materials, public_offers
from core.models import City


def _fmt(v):
    v = Decimal(v).quantize(Decimal("0.01"))
    return f"{v.normalize():f}"


def _text_hit(obj, word, fields):
    pattern = re.compile(ar_regex(word), re.IGNORECASE)
    return any(pattern.search(str(f(obj) or "")) for f in fields)


class Condition:
    def __init__(self, key, label, q, check):
        self.key, self.label, self.q, self.check = key, label, q, check


def build(criteria, target):
    """Return (mandatory, preferences) lists of Condition."""
    is_offer = target == "offers"
    loc = "business" if is_offer else "supplier"
    mand, pref = [], []

    if criteria.get("max_price") is not None:
        mp = Decimal(str(criteria["max_price"]))
        mand.append(Condition(
            "max_price", f"السعر لا يزيد عن {_fmt(mp)} ₪", Q(price__lte=mp),
            lambda o, mp=mp: (o.price <= mp, f"السعر {_fmt(o.price)} ₪ أعلى من الحد {_fmt(mp)} ₪"),
        ))
    if criteria.get("min_price") is not None:
        mn = Decimal(str(criteria["min_price"]))
        mand.append(Condition(
            "min_price", f"السعر لا يقل عن {_fmt(mn)} ₪", Q(price__gte=mn),
            lambda o, mn=mn: (o.price >= mn, f"السعر {_fmt(o.price)} ₪ أقل من {_fmt(mn)} ₪"),
        ))
    if criteria.get("category_ids"):
        ids = list(criteria["category_ids"])
        names = "، ".join(Category.objects.filter(pk__in=ids).values_list("name", flat=True))
        mand.append(Condition(
            "category", f"التصنيف: {names}", Q(category_id__in=ids),
            lambda o, ids=ids: (o.category_id in ids, f"التصنيف «{o.category.name}» مختلف"),
        ))
    if criteria.get("max_days") is not None:
        d = int(criteria["max_days"])
        if is_offer:
            mand.append(Condition(
                "max_days", f"جاهز خلال {d} يوم/أيام", Q(preparation_days__lte=d),
                lambda o, d=d: (o.preparation_days <= d, f"مدة التجهيز {o.preparation_days} يوم أطول من {d}"),
            ))
        else:
            mand.append(Condition(
                "max_days", f"يصل خلال {d} يوم/أيام",
                Q(supplier__delivery_available=True, supplier__delivery_days__lte=d),
                lambda o, d=d: (
                    o.supplier.delivery_available and o.supplier.delivery_days is not None and o.supplier.delivery_days <= d,
                    "مدة التوصيل غير معروفة" if o.supplier.delivery_days is None else f"مدة التوصيل {o.supplier.delivery_days} يوم أطول من {d}",
                ),
            ))
    if criteria.get("offer_type") and is_offer:
        t = criteria["offer_type"]
        mand.append(Condition(
            "offer_type", f"النوع: {Offer.OfferType(t).label}", Q(offer_type=t),
            lambda o, t=t: (o.offer_type == t, f"النوع «{o.get_offer_type_display()}»"),
        ))
    if criteria.get("min_rating") is not None and is_offer:
        r = Decimal(str(criteria["min_rating"]))
        mand.append(Condition(
            "min_rating", f"تقييم {r} فأعلى", Q(business__rating_avg__gte=r),
            lambda o, r=r: (o.business.rating_avg >= r, f"التقييم {o.business.rating_avg} أقل من {r}"),
        ))
    if criteria.get("needs_delivery"):
        mand.append(Condition(
            "delivery", "يوفر التوصيل", Q(**{f"{loc}__delivery_available": True}),
            lambda o: (getattr(o, loc).delivery_available, "لا يوفر التوصيل"),
        ))
    if criteria.get("city_id"):
        cid = criteria["city_id"]
        cname = City.objects.filter(pk=cid).values_list("name", flat=True).first() or ""
        cond = Condition(
            "city", f"من {cname}", Q(**{f"{loc}__city_id": cid}),
            lambda o, cid=cid: (getattr(o, loc).city_id == cid, f"الموقع {getattr(o, loc).city.name} وليس {cname}"),
        )
        (pref if criteria.get("city_is_preference", True) else mand).append(cond)
    fields = (
        [lambda o: o.title, lambda o: o.description, lambda o: o.category.name]
        if is_offer else
        [lambda o: o.title, lambda o: o.description, lambda o: o.specifications, lambda o: o.category.name]
    )
    for kw in criteria.get("keywords", [])[:6]:
        pref.append(Condition(
            f"kw:{kw}", f"يحتوي «{kw}»",
            keyword_q(kw, ["title", "description", "category__name"]),
            lambda o, kw=kw: (_text_hit(o, kw, fields), f"لا يذكر «{kw}»"),
        ))
    return mand, pref


def run(criteria, target, limit=10):
    is_offer = target == "offers"
    base = public_offers() if is_offer else public_materials()
    base = base.filter(is_available=True)
    if is_offer:
        from django.db.models import F

        base = base.filter(~Q(offer_type=Offer.OfferType.READY) | Q(stock_quantity__gt=F("reserved_quantity")))
    else:
        from django.db.models import F

        base = base.filter(stock_quantity__gt=F("reserved_quantity"))

    mand, pref = build(criteria, target)

    def evaluate(obj):
        met, unmet = [], []
        for c in mand:
            ok, why = c.check(obj)
            (met if ok else unmet).append(c.label if ok else why)
        pref_met, pref_unmet = [], []
        for c in pref:
            ok, why = c.check(obj)
            (pref_met if ok else pref_unmet).append(c.label if ok else why)
        score = len(pref_met) * 10 - len(unmet) * 100
        if criteria.get("prefer_cheap"):
            score -= float(obj.price) / 1000
        if is_offer:
            score += float(obj.business.rating_avg)
        return {"met": met, "unmet": unmet, "pref_met": pref_met, "pref_unmet": pref_unmet, "score": score}

    full_q = Q()
    for c in mand:
        full_q &= c.q
    full = list(base.filter(full_q)[:200])
    results = []
    for obj in full:
        ev = evaluate(obj)
        results.append({"obj": obj, "match": "full", **ev})
    if not mand and any(p.key.startswith("kw:") for p in pref):
        # Nothing strict was requested: keep only records that relate to the words used
        results = [r for r in results if r["pref_met"]]
    results.sort(key=lambda r: -r["score"])
    results = results[:limit]

    near = []
    if len(results) < 3 and mand:
        # Closest records: satisfy at least one mandatory condition or a keyword
        any_q = Q()
        for c in mand + [p for p in pref if p.key.startswith("kw:")]:
            any_q |= c.q
        seen = {r["obj"].pk for r in results}
        candidates = [o for o in base.filter(any_q)[:300] if o.pk not in seen]
        for obj in candidates:
            ev = evaluate(obj)
            if ev["unmet"]:
                near.append({"obj": obj, "match": "near", **ev})
        near.sort(key=lambda r: (len(r["unmet"]), -r["score"]))
        near = near[: max(0, 5 - len(results))]

    return {
        "mandatory": [c.label for c in mand],
        "preferences": [c.label for c in pref],
        "results": results + near,
        "full_count": len(results),
    }

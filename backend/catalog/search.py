"""Ordinary search for offers and raw materials (works without AI)."""
import re
from decimal import Decimal, InvalidOperation

from django.db.models import F, Q

from .models import Offer, ProfileStatus

_VARIANTS = [
    ("اأإآ", "[اأإآ]"),
    ("هة", "[هة]"),
    ("يى", "[يى]"),
    ("وؤ", "[وؤ]"),
]
_DIACRITICS = re.compile(r"[ً-ْـ]")


def normalize_ar(text):
    text = _DIACRITICS.sub("", text or "")
    return text.strip()


def ar_regex(word):
    """Build a case-insensitive regex that tolerates common Arabic spelling variants."""
    out = []
    for ch in normalize_ar(word):
        for chars, cls in _VARIANTS:
            if ch in chars:
                out.append(cls)
                break
        else:
            out.append(re.escape(ch))
    return "".join(out)


def keyword_q(q, fields):
    cond = Q()
    for word in normalize_ar(q).split():
        if len(word) < 2:
            continue
        if len(word) > 3 and word[-1] in "ةه":
            word = word[:-1]  # «مطرزة» also finds «مطرز»
        pattern = ar_regex(word)
        wq = Q()
        for f in fields:
            wq |= Q(**{f"{f}__iregex": pattern})
        cond &= wq
    return cond


def _dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _int(v):
    if v in (None, ""):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _bool(v):
    return str(v).lower() in ("1", "true", "yes", "on")


OFFER_ORDERING = {
    "price": ["price", "-id"],
    "-price": ["-price", "-id"],
    "rating": ["-business__rating_avg", "-id"],
    "newest": ["-created_at"],
    "prep": ["preparation_days", "price"],
}


def public_offers():
    return Offer.objects.filter(is_deleted=False, business__status=ProfileStatus.ACTIVE).select_related(
        "business", "business__city", "business__area", "category"
    ).prefetch_related("images")


def search_offers(params, qs=None):
    qs = public_offers() if qs is None else qs
    q = params.get("q")
    if q:
        qs = qs.filter(keyword_q(q, ["title", "description", "business__name", "category__name"]))
    if (v := _int(params.get("category"))) is not None:
        qs = qs.filter(category_id=v)
    if (v := _int(params.get("city"))) is not None:
        qs = qs.filter(business__city_id=v)
    if (v := _int(params.get("area"))) is not None:
        qs = qs.filter(business__area_id=v)
    if (v := _int(params.get("business"))) is not None:
        qs = qs.filter(business_id=v)
    if (v := _dec(params.get("min_price"))) is not None:
        qs = qs.filter(price__gte=v)
    if (v := _dec(params.get("max_price"))) is not None:
        qs = qs.filter(price__lte=v)
    if (v := _dec(params.get("min_rating"))) is not None:
        qs = qs.filter(business__rating_avg__gte=v)
    if (v := _int(params.get("max_prep_days"))) is not None:
        qs = qs.filter(preparation_days__lte=v)
    offer_type = params.get("offer_type")
    if offer_type in Offer.OfferType.values:
        qs = qs.filter(offer_type=offer_type)
    if _bool(params.get("available")):
        qs = qs.filter(is_available=True).filter(
            ~Q(offer_type=Offer.OfferType.READY) | Q(stock_quantity__gt=F("reserved_quantity"))
        )
    if _bool(params.get("delivery")):
        qs = qs.filter(business__delivery_available=True)
    ordering = OFFER_ORDERING.get(params.get("ordering") or "newest", OFFER_ORDERING["newest"])
    return qs.order_by(*ordering)


MATERIAL_ORDERING = {
    "price": ["price", "-id"],
    "-price": ["-price", "-id"],
    "newest": ["-created_at"],
    "delivery": ["supplier__delivery_days", "price"],
}


def public_materials():
    from suppliers.models import Material

    return Material.objects.filter(is_deleted=False, supplier__status=ProfileStatus.ACTIVE).select_related(
        "supplier", "supplier__city", "supplier__area", "category"
    ).prefetch_related("images")


def search_materials(params, qs=None):
    from suppliers.models import Material

    qs = public_materials() if qs is None else qs
    q = params.get("q")
    if q:
        qs = qs.filter(keyword_q(q, ["title", "description", "specifications", "supplier__name", "category__name"]))
    if (v := _int(params.get("category"))) is not None:
        qs = qs.filter(category_id=v)
    if (v := _int(params.get("city"))) is not None:
        qs = qs.filter(supplier__city_id=v)
    if (v := _int(params.get("supplier"))) is not None:
        qs = qs.filter(supplier_id=v)
    unit = params.get("unit")
    if unit in Material.Unit.values:
        qs = qs.filter(unit=unit)
    if (v := _dec(params.get("min_price"))) is not None:
        qs = qs.filter(price__gte=v)
    if (v := _dec(params.get("max_price"))) is not None:
        qs = qs.filter(price__lte=v)
    if (v := _dec(params.get("min_available"))) is not None:
        qs = qs.filter(stock_quantity__gte=F("reserved_quantity") + v)
    if (v := _int(params.get("max_prep_days"))) is not None:
        qs = qs.filter(preparation_days__lte=v)
    if (v := _int(params.get("max_delivery_days"))) is not None:
        qs = qs.filter(supplier__delivery_available=True, supplier__delivery_days__lte=v)
    if _bool(params.get("delivery")):
        qs = qs.filter(supplier__delivery_available=True)
    if _bool(params.get("available")):
        qs = qs.filter(is_available=True, stock_quantity__gt=F("reserved_quantity"))
    ordering = MATERIAL_ORDERING.get(params.get("ordering") or "newest", MATERIAL_ORDERING["newest"])
    return qs.order_by(*ordering)

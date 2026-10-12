from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from catalog.models import Category, Offer
from catalog.search import normalize_ar
from catalog.serializers import OfferPublicSerializer
from core.models import City
from core.permissions import HasBusinessProfile
from reports.service import business_report
from suppliers.serializers import MaterialPublicSerializer

from . import matcher, parser, provider


class AIStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "external_ai_enabled": provider.is_configured(),
            "message": "المساعد يعمل بنموذج Claude." if provider.is_configured()
            else "المساعد يعمل بالقواعد المدمجة (لا يوجد مفتاح ذكاء اصطناعي).",
        })


class SmartSearchInput(serializers.Serializer):
    text = serializers.CharField(max_length=500)
    target = serializers.ChoiceField(choices=["offers", "materials"], default="offers")


def _ai_to_criteria(data, categories, cities):
    """Validate AI output against real categories/cities; drop anything unknown."""
    cat_map = {normalize_ar(n): cid for cid, n in categories}
    city_map = {normalize_ar(n): cid for cid, n in cities}

    def num(v, lo=0, hi=1_000_000):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        return v if lo <= v <= hi else None

    crit = {
        "keywords": [str(k)[:30] for k in (data.get("keywords") or []) if str(k).strip()][:6],
        "category_ids": [cat_map[normalize_ar(n)] for n in (data.get("category_names") or []) if normalize_ar(n) in cat_map],
        "city_id": city_map.get(normalize_ar(data.get("city_name") or "")),
        "city_is_preference": bool(data.get("city_is_preference", True)),
        "max_price": num(data.get("max_price")),
        "min_price": num(data.get("min_price")),
        "max_days": int(d) if (d := num(data.get("max_days"), 0, 365)) is not None else None,
        "offer_type": data.get("offer_type") if data.get("offer_type") in Offer.OfferType.values else None,
        "min_rating": num(data.get("min_rating"), 0, 5),
        "needs_delivery": bool(data.get("needs_delivery")),
        "prefer_cheap": bool(data.get("prefer_cheap")),
    }
    return crit


class SmartSearchView(APIView):
    """Natural-language Arabic search over real records."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def post(self, request):
        ser = SmartSearchInput(data=request.data)
        ser.is_valid(raise_exception=True)
        text, target = ser.validated_data["text"], ser.validated_data["target"]
        kind = Category.Kind.OFFER if target == "offers" else Category.Kind.MATERIAL
        categories = list(Category.objects.filter(kind=kind, is_active=True).values_list("id", "name"))
        cities = list(City.objects.filter(is_active=True).values_list("id", "name"))
        user_city = getattr(request.user, "city_id", None) if request.user.is_authenticated else None

        source = "rules"
        criteria = None
        if provider.is_configured():
            data = provider.extract_criteria(text, target, [n for _, n in categories], [n for _, n in cities])
            if data is not None:
                criteria = _ai_to_criteria(data, categories, cities)
                source = "ai"
        if criteria is None:
            criteria = parser.parse(text, target, categories, cities, user_city)

        out = matcher.run(criteria, target)
        Ser = OfferPublicSerializer if target == "offers" else MaterialPublicSerializer
        results = []
        for r in out["results"]:
            results.append({
                "item": Ser(r["obj"], context={"request": request}).data,
                "match": r["match"],
                "reasons": r["met"] + r["pref_met"],
                "unmet": r["unmet"] + r["pref_unmet"],
            })
        if out["full_count"]:
            message = f"وجدنا {out['full_count']} نتيجة تطابق الشروط الإلزامية."
        elif results:
            message = "لا يوجد تطابق كامل؛ هذه أقرب الخيارات مع توضيح ما لا يتطابق."
        else:
            message = "لا توجد عروض مناسبة حاليًا. جرّب تخفيف الشروط."
        return Response({
            "source": source,
            "criteria": {"mandatory": out["mandatory"], "preferences": out["preferences"]},
            "message": message,
            "results": results,
        })


class MarketingDraftView(APIView):
    """Draft a marketing description from the owner's real offer data. Never saved automatically."""

    permission_classes = [HasBusinessProfile]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def post(self, request):
        offer_id = request.data.get("offer_id")
        offer = Offer.objects.filter(pk=offer_id, business=request.user.business_profile, is_deleted=False).select_related(
            "category", "business__city"
        ).first()
        if offer is None:
            return Response({"detail": "العرض غير موجود."}, status=404)
        facts = {
            "العنوان": offer.title,
            "الوصف الحالي": offer.description,
            "التصنيف": offer.category.name,
            "النوع": offer.get_offer_type_display(),
            "السعر": f"{offer.price} ₪ {offer.price_unit}",
            "مدة التجهيز بالأيام": offer.preparation_days,
            "مدة الخدمة": offer.service_duration or None,
            "المدينة": offer.business.city.name,
            "اسم المشروع": offer.business.name,
            "ملاحظات إضافية من صاحب المشروع": str(request.data.get("extra_facts", ""))[:500] or None,
        }
        facts = {k: v for k, v in facts.items() if v not in (None, "")}
        draft = provider.write_marketing_draft(facts) if provider.is_configured() else None
        source = "ai"
        if not draft:
            source = "template"
            prep = "جاهز فورًا" if offer.preparation_days == 0 else f"يُجهَّز خلال {offer.preparation_days} يوم"
            draft = (
                f"{offer.title} من {offer.business.name} في {offer.business.city.name}. "
                f"{offer.description.strip() + ' ' if offer.description.strip() else ''}"
                f"ضمن تصنيف {offer.category.name}، {offer.get_offer_type_display()}، {prep}. "
                f"السعر {offer.price} ₪ {offer.price_unit}. اطلبه الآن عبر مهنتي."
            )
        return Response({
            "draft": draft,
            "source": source,
            "facts": facts,
            "note": "هذه مسودة فقط. راجعها وعدّلها، ثم احفظها في وصف العرض إن أردت نشرها.",
        })


class BusinessSummaryView(APIView):
    """Summary of real sales/orders/stock. Numbers are computed in code."""

    permission_classes = [HasBusinessProfile]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def get(self, request):
        period = request.query_params.get("period", "week")
        rep = business_report(request.user.business_profile, period)
        figures = {
            "الفترة": rep["period"]["label"],
            "الطلبات المكتملة": rep["completed_orders"],
            "الإيرادات ₪": str(rep["revenue"]),
            "تكلفة المباع ₪": str(rep["cost_of_goods_sold"]),
            "المصاريف ₪": str(rep["expenses_total"]),
            "الربح التشغيلي التقديري ₪": str(rep["estimated_operating_profit"]),
            "التكاليف ناقصة": rep["costs_incomplete"],
            "الطلبات المفتوحة": rep["open_orders"],
            "عناصر مخزون منخفض": rep["low_stock_items"],
            "الأكثر مبيعًا": [b["title"] for b in rep["best_sellers"][:3]],
        }
        text = provider.phrase_summary(figures) if provider.is_configured() else None
        source = "ai"
        if not text:
            source = "template"
            best = "، ".join(figures["الأكثر مبيعًا"]) or "لا يوجد بعد"
            text = (
                f"خلال {rep['period']['label']}: أكملت {rep['completed_orders']} طلبًا بإيرادات {rep['revenue']} ₪. "
                f"الربح التشغيلي التقديري {rep['estimated_operating_profit']} ₪"
                f"{' (التكاليف المسجلة ناقصة)' if rep['costs_incomplete'] else ''}. "
                f"لديك {rep['open_orders']} طلبًا مفتوحًا و{rep['low_stock_items']} عنصرًا بمخزون منخفض. "
                f"الأكثر مبيعًا: {best}."
            )
        return Response({"summary": text, "source": source, "figures": figures, "report": rep})

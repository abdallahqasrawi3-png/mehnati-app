"""Isolated connection to the external AI provider (Claude via the Anthropic SDK).

* The API key stays on the server (ANTHROPIC_API_KEY env var).
* Every function returns None on any problem; callers then use the built-in
  rule-based logic, so the app keeps working without a key or during outages.
* Only the minimum needed text is sent (search text, public offer facts or
  aggregated numbers) - never names, phones, addresses or emails.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def is_configured():
    return bool(settings.ANTHROPIC_API_KEY)


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY, timeout=settings.AI_TIMEOUT_SECONDS, max_retries=1
        )
    return _client


def _call(system, user_text, *, max_tokens=2000, schema=None):
    if not is_configured():
        return None
    import anthropic

    kwargs = {
        "model": settings.AI_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
        "output_config": {"effort": "low"},
        # Server-side refusal fallback routes declined requests to a suitable model.
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
    }
    if schema is not None:
        kwargs["output_config"]["format"] = {"type": "json_schema", "schema": schema}
    try:
        response = _get_client().beta.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        logger.error("AI provider rejected the API key")
        return None
    except anthropic.RateLimitError:
        logger.warning("AI provider rate limited")
        return None
    except anthropic.APIStatusError as e:
        logger.warning("AI provider error status=%s", e.status_code)
        return None
    except anthropic.APIConnectionError:
        logger.warning("AI provider unreachable")
        return None
    except Exception:
        logger.exception("AI provider unexpected failure")
        return None
    if response.stop_reason in ("refusal", "max_tokens"):
        logger.warning("AI provider stop_reason=%s", response.stop_reason)
        return None
    text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
    return text or None


CRITERIA_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {"type": "array", "items": {"type": "string"}},
        "category_names": {"type": "array", "items": {"type": "string"}},
        "city_name": {"type": ["string", "null"]},
        "city_is_preference": {"type": "boolean"},
        "max_price": {"type": ["number", "null"]},
        "min_price": {"type": ["number", "null"]},
        "max_days": {"type": ["integer", "null"]},
        "offer_type": {"type": ["string", "null"], "enum": ["ready", "made_to_order", "service", None]},
        "min_rating": {"type": ["number", "null"]},
        "needs_delivery": {"type": "boolean"},
        "prefer_cheap": {"type": "boolean"},
    },
    "required": [
        "keywords", "category_names", "city_name", "city_is_preference", "max_price", "min_price",
        "max_days", "offer_type", "min_rating", "needs_delivery", "prefer_cheap",
    ],
    "additionalProperties": False,
}


def extract_criteria(text, target, category_names, city_names):
    system = (
        "أنت محلل طلبات بحث لمنصة «مهنتي» للمشاريع المنزلية. حوّل طلب المستخدم العربي إلى معايير بحث فقط. "
        "لا تخترع قيمًا غير مذكورة. اختر التصنيفات والمدن من القوائم المعطاة فقط وبنفس الكتابة. "
        "max_price حد أعلى إلزامي للسعر إن ذُكر. max_days: مدة التجهيز القصوى بالأيام للمنتجات، "
        "أو مدة وصول التوصيل للمواد الخام. city_is_preference=true إذا قال المستخدم «يفضل» أو ما يشبهها. "
        "keywords: كلمات مهمة تصف الشيء المطلوب (بدون كلمات عامة)."
    )
    user = json.dumps(
        {
            "request": text[:500],
            "search_target": "منتجات وخدمات" if target == "offers" else "مواد خام",
            "allowed_categories": category_names,
            "allowed_cities": city_names,
        },
        ensure_ascii=False,
    )
    raw = _call(system, user, max_tokens=1500, schema=CRITERIA_SCHEMA)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_marketing_draft(facts):
    system = (
        "اكتب وصفًا تسويقيًا عربيًا قصيرًا وجذابًا (60 إلى 120 كلمة) لعرض في منصة «مهنتي». "
        "استخدم الحقائق المعطاة فقط. لا تضف أسعارًا أو خصومات أو مواد أو مواعيد أو ادعاءات غير موجودة في الحقائق. "
        "أعد النص فقط دون عناوين أو علامات تنسيق."
    )
    return _call(system, json.dumps(facts, ensure_ascii=False, default=str), max_tokens=1200)


def phrase_summary(figures):
    system = (
        "لخّص هذه الأرقام لصاحب مشروع منزلي بالعربية في 3 إلى 5 جمل بسيطة مع نصيحة عملية واحدة. "
        "انسخ الأرقام كما هي تمامًا ولا تحسب أرقامًا جديدة ولا تخترع بيانات."
    )
    return _call(system, json.dumps(figures, ensure_ascii=False, default=str), max_tokens=1200)

"""Django settings for Mehnaty. Secrets come from environment variables (.env)."""
from datetime import timedelta
from pathlib import Path
import os
import sys

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "core",
    "accounts",
    "catalog",
    "suppliers",
    "orders",
    "inventory",
    "shipping",
    "reviews",
    "notifications",
    "reports",
    "ai_assistant",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves /static (admin CSS/JS) in production
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mehnaty.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mehnaty.wsgi.application"

def clean_database_url(raw):
    """Accept common paste mistakes in hosting dashboards:
    `DATABASE_URL=postgresql://...`, quotes around the value, or Neon's `psql 'postgresql://...'`."""
    value = (raw or "").strip()
    if value.lower().startswith("psql "):
        value = value[5:].strip()
    head = value.split("://", 1)[0]
    if "=" in head:  # "DATABASE_URL=postgresql://..."
        value = value.split("=", 1)[1].strip()
    return value.strip("'\"").strip()


def database_from_url(url):
    """postgresql://user:pass@host:port/name?sslmode=require&... -> Django DATABASES entry.

    Query parameters (sslmode, channel_binding, ...) are passed to the driver. Hosts with
    "-pooler" (Neon's PgBouncer) disable server-side cursors, which transaction pooling can't hold.
    """
    from urllib.parse import parse_qsl, unquote, urlsplit

    url = clean_database_url(url)
    parts = urlsplit(url)
    if parts.scheme not in ("postgres", "postgresql"):
        # Show only the beginning (never the password) to help spot the mistake.
        start = url.split(":", 1)[0][:15]
        raise RuntimeError(
            f"DATABASE_URL must be a link that starts with postgresql:// (yours starts with {start!r}). "
            "Paste only the link, without quotes, 'psql' or 'DATABASE_URL='."
        )
    pooled = "-pooler" in (parts.hostname or "")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parts.path.lstrip("/")),
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": parts.hostname or "",
        "PORT": str(parts.port or 5432),
        "OPTIONS": dict(parse_qsl(parts.query)),
        # Keep connections open between requests: a new TLS connection to a cloud database costs
        # hundreds of milliseconds. Behind a pooler (transaction mode), avoid server-side cursors.
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "DISABLE_SERVER_SIDE_CURSORS": pooled,
    }


# DATABASE_URL (e.g. a Neon cloud database) takes priority; otherwise the local DB_* settings.
# USE_LOCAL_DB=1 forces the local database (handy for running the test suite offline and fast).
if os.getenv("DATABASE_URL", "").strip() and os.getenv("USE_LOCAL_DB") != "1":
    DATABASES = {"default": database_from_url(os.getenv("DATABASE_URL").strip())}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "mehnaty"),
            "USER": os.getenv("DB_USER", "mehnaty"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "العربية")]
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Hebron")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Compressed, cache-busted static files served by WhiteNoise (run collectstatic on deploy).
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
# Hosting without a separate file server (e.g. Render): let Django serve uploaded images.
# Note: such disks are often temporary; use persistent storage for real deployments.
SERVE_MEDIA = DEBUG or env_bool("SERVE_MEDIA", False)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploads: images only, size-limited (validated again in core.validators)
MAX_IMAGE_UPLOAD_MB = int(os.getenv("MAX_IMAGE_UPLOAD_MB", "5"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "300/min"),
        "user": os.getenv("THROTTLE_USER", "1200/min"),
        "auth": os.getenv("THROTTLE_AUTH", "20/min"),
        "ai": os.getenv("THROTTLE_AI", "30/min"),
        "contact": os.getenv("THROTTLE_CONTACT", "10/hour"),
    },
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

if "test" in sys.argv:
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {k: "100000/min" for k in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081")
CORS_ALLOW_ALL_ORIGINS = DEBUG and env_bool("CORS_ALLOW_ALL_IN_DEBUG", True)
# HTTPS origins allowed to submit forms (Django admin login), e.g. https://mehnati-api.onrender.com
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

# Production hardening (HTTPS)
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]  # hosting health checks call this over plain HTTP
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# AI (optional). The app works fully without a key.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "claude-opus-5-5")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))

# Administrator's WhatsApp for the "contact the administrator" form (international format, digits only).
# Accepts 00972..., +972... or 972...; reports open WhatsApp with the details pre-filled for this number.
ADMIN_WHATSAPP = "".join(ch for ch in os.getenv("ADMIN_WHATSAPP", "972569228977") if ch.isdigit()).removeprefix("00")

# Shipping: the simulator is for tests/demo only and is never a real carrier.
SHIPPING_SIMULATOR_ENABLED = env_bool("SHIPPING_SIMULATOR_ENABLED", False)

CURRENCY_CODE = "ILS"
CURRENCY_SYMBOL = "₪"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {"django.request": {"level": "ERROR"}},
}

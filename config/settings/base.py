"""
Paramètres Django partagés — architecture production-ready.
"""
from pathlib import Path

import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "172.26.154.81"]),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-change-in-production")
DEBUG = env("DEBUG")
# Valeur du .env si présente ; sinon hôtes locaux et production
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "172.26.154.81", "*.onrender.com", "*.railway.app"])

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "channels",
    "apps.users",
    "apps.couples",
    "apps.game",
    "apps.ai",
    "apps.payments",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.game.context_processors.gamification",
            ],
        },
    },
]

AUTH_USER_MODEL = "users.User"
LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "couples:dashboard"
LOGOUT_REDIRECT_URL = "core:welcome"

# CSRF Configuration for AJAX requests
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://*.onrender.com",
    "https://*.railway.app",
]
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Database configuration - PostgreSQL in production, SQLite in development
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# Sécurité pour éliminer toute option "timeout" ou "connect_timeout" parasite
if 'OPTIONS' in DATABASES['default']:
    DATABASES['default']['OPTIONS'].pop('timeout', None)
    DATABASES['default']['OPTIONS'].pop('connect_timeout', None)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Channels — WebSocket temps réel
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://127.0.0.1:6379/0")]},
    },
}

# Celery
CELERY_BROKER_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Gamification & limites freemium (quota partagé par couple)
FREE_DAILY_QUESTIONS = 7
PREMIUM_MONTHLY_PRICE = 5  # legacy affichage
PREMIUM_CURRENCY = "USD"

# Abonnements couple
WEEKLY_PREMIUM_PRICE = env("WEEKLY_PREMIUM_PRICE", default="1.99")
WEEKEND_PASS_PRICE = env("WEEKEND_PASS_PRICE", default="0.50")
WEEKLY_PREMIUM_DAYS = env.int("WEEKLY_PREMIUM_DAYS", default=7)

# KibaWallet — Mobile Money RDC (clés sk_live_ uniquement côté serveur)
KIBA_API_BASE_URL = env("KIBA_API_BASE_URL", default="https://kibawallet-api.onrender.com")
KIBA_PUBLIC_KEY = env("KIBA_PUBLIC_KEY", default="")
KIBA_SECRET_KEY = env("KIBA_SECRET_KEY", default="")
KIBA_WEBHOOK_SECRET = env("KIBA_WEBHOOK_SECRET", default="")
KIBA_REQUEST_TIMEOUT = env.int("KIBA_REQUEST_TIMEOUT", default=30)

# Publicités récompensées
REWARDED_AD_EXTRA_QUESTIONS = env.int("REWARDED_AD_EXTRA_QUESTIONS", default=5)
REWARDED_AD_SIMULATION_SECONDS = env.int("REWARDED_AD_SIMULATION_SECONDS", default=30)
REWARDED_AD_MAX_UNLOCKS_PER_DAY = env.int("REWARDED_AD_MAX_UNLOCKS_PER_DAY", default=10)

# Moteur de jeu — délai avant question suivante automatique (secondes)
GAME_AUTO_NEXT_SECONDS = env.int("GAME_AUTO_NEXT_SECONDS", default=10)
# Nombre de questions répondues à deux pour passer au niveau suivant
QUESTIONS_PER_LEVEL = env.int("QUESTIONS_PER_LEVEL", default=21)

# IA — Groq (prioritaire) ou Gemini (legacy)
AI_PROVIDER = env("AI_PROVIDER", default="groq")
GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_MODEL = env("GROQ_MODEL", default="llama-3.1-8b-instant")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="") or env("AI_GEMINI_API_KEY", default="")
AI_GEMINI_API_KEY = GEMINI_API_KEY  # rétrocompatibilité
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-2.0-flash")

# PWA
PWA_APP_NAME = "K'er — Jeux de couple"
PWA_SHORT_NAME = "K'er"
PWA_THEME_COLOR = "#0d0509"
PWA_BACKGROUND_COLOR = "#0d0509"
AI_REQUEST_TIMEOUT = env.int("AI_REQUEST_TIMEOUT", default=30)

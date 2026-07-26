"""Paramètres développement — SQLite, debug activé."""
from .base import *  # noqa: F403

DEBUG = False

# Téléphone / tablette sur le Wi‑Fi : évite DisallowedHost (IP LAN change souvent)
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        **env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),  # noqa: F405
        "OPTIONS": {
            "timeout": 30,
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ker-dev",
    },
}

# Fallback mémoire si Redis indisponible en local
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

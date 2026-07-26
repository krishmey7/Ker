"""Paramètres production – PostgreSQL, sécurité renforcée."""
from urllib.parse import urlparse
from .base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Récupération de la base via parsing manuel (sans dj_database_url pour éviter timeout)
db_url = env('DATABASE_URL', default=None)

if db_url:
    # Parse manuel avec urllib.parse pour éviter toute option non supportée
    parsed = urlparse(db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username or '',
            'PASSWORD': parsed.password or '',
            'HOST': parsed.hostname or '',
            'PORT': parsed.port or '',
            'CONN_MAX_AGE': 600,
            'OPTIONS': {},
        }
    }
else:
    # Fallback si pas de DATABASE_URL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
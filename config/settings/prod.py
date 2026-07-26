"""Paramètres production – PostgreSQL, sécurité renforcée."""
import dj_database_url
from .base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Récupération de la base via dj-database-url (plus fiable sur Render)
# Parsing manuel pour éviter les options non supportées par psycopg2
db_url = env('DATABASE_URL', default=None)

if db_url:
    # Parse l'URL et reconstruit avec seulement les options supportées
    parsed = dj_database_url.parse(db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.get('NAME', ''),
            'USER': parsed.get('USER', ''),
            'PASSWORD': parsed.get('PASSWORD', ''),
            'HOST': parsed.get('HOST', ''),
            'PORT': parsed.get('PORT', ''),
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
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
DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        ssl_require=False
    )
}

# ⚠️ Nettoyage strict des options incompatibles avec psycopg2
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS'].pop('timeout', None)
DATABASES['default']['OPTIONS'].pop('connect_timeout', None)
DATABASES['default'].pop('timeout', None)
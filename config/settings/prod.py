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

# --- Static files / WhiteNoise configuration ---
# Use compressed manifest storage to serve versioned static files in production.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default long cache for static assets (other than SW); we will explicitly
# prevent aggressive caching for the service worker below.
WHITENOISE_MAX_AGE = 31536000  # 1 year


# Middleware to ensure service-worker is served without aggressive caching.
# It is appended to MIDDLEWARE so it runs after WhiteNoise has served the file
# and can override the `Cache-Control` header for the SW URL(s).
class ServiceWorkerNoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            path = request.path or ''
            if path.endswith('/service-worker.js') or path.endswith('/static/js/service-worker.js') or 'service-worker.js?v=' in path:
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
        except Exception:
            # don't break the request pipeline if something unexpected happens
            pass
        return response

# Ensure our middleware runs after existing middleware (WhiteNoise is defined in base settings)
MIDDLEWARE = MIDDLEWARE + ['config.settings.prod.ServiceWorkerNoCacheMiddleware']
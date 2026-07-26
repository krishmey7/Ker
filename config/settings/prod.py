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
# 1. Parsing propre de l'URL
db_config = dj_database_url.config(
    conn_max_age=600,
    ssl_require=False
)

# 2. Suppression de toutes les options non supportées par psycopg2
unsupported_options = ['timeout', 'connect_timeout', 'options']
for key in list(db_config.keys()):
    if key in unsupported_options:
        del db_config[key]

# 3. Nettoyage complet du sous-dictionnaire OPTIONS s'il existe
if 'OPTIONS' in db_config:
    for opt_key in list(db_config['OPTIONS'].keys()):
        if opt_key in ['timeout', 'connect_timeout', 'sslmode']:
            db_config['OPTIONS'].pop(opt_key, None)

DATABASES = {
    'default': db_config
}
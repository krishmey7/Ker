"""Configuration Celery pour tâches asynchrones (batch IA, notifications)."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("ker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

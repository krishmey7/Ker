"""Vues PWA — service worker et manifest servis à la racine (scope complet)."""
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView


class OfflineView(TemplateView):
    """Page hors ligne — fallback navigation."""

    template_name = "offline.html"


def serve_service_worker(request):
    """Sert le service worker à la racine pour couvrir toute l'app."""
    path = Path(settings.BASE_DIR) / "static" / "js" / "service-worker.js"
    content = path.read_text(encoding="utf-8")
    response = HttpResponse(content, content_type="application/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def serve_manifest(request):
    """Manifest PWA dynamique (nom et couleurs depuis settings)."""
    import json

    path = Path(settings.BASE_DIR) / "static" / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["name"] = getattr(settings, "PWA_APP_NAME", data.get("name", "K'er"))
    data["short_name"] = getattr(settings, "PWA_SHORT_NAME", data.get("short_name", "K'er"))
    data["theme_color"] = getattr(settings, "PWA_THEME_COLOR", data.get("theme_color", "#0d0509"))
    data["background_color"] = getattr(
        settings, "PWA_BACKGROUND_COLOR", data.get("background_color", "#0d0509")
    )
    content = json.dumps(data, ensure_ascii=False, indent=2)
    response = HttpResponse(content, content_type="application/manifest+json; charset=utf-8")
    response["Cache-Control"] = "public, max-age=3600"
    return response

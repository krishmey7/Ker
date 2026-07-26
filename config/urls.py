"""Routage URL principal."""
from django.contrib import admin
from django.urls import include, path

from apps.game.pwa_views import OfflineView, serve_manifest, serve_service_worker

urlpatterns = [
    path("admin/", admin.site.urls),
    path("service-worker.js", serve_service_worker, name="service_worker"),
    path("manifest.json", serve_manifest, name="manifest"),
    path("offline/", OfflineView.as_view(), name="offline"),
    path("", include("apps.game.urls", namespace="core")),
    path("users/", include("apps.users.urls", namespace="users")),
    path("couple/", include("apps.couples.urls", namespace="couples")),
    path("game/", include("apps.game.urls_game", namespace="game")),
    path("payments/", include("apps.payments.urls", namespace="payments")),
]

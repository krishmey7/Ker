"""Notifications push — modèle pour abonnements Web Push."""
from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    """Endpoint Web Push par utilisateur."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.TextField()
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "endpoint")]

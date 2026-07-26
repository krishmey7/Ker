"""Service notifications — rappels quotidiens (stub)."""
from apps.notifications.models import PushSubscription


class PushNotificationService:
    """Envoi push — à compléter avec pywebpush."""

    @staticmethod
    def register(user, subscription_info: dict) -> PushSubscription:
        """Enregistre un abonnement navigateur."""
        return PushSubscription.objects.update_or_create(
            user=user,
            endpoint=subscription_info["endpoint"],
            defaults={
                "p256dh": subscription_info["keys"]["p256dh"],
                "auth": subscription_info["keys"]["auth"],
            },
        )[0]

    @staticmethod
    def send_daily_reminder(user) -> bool:
        """Envoie un rappel de question du jour."""
        # TODO: pywebpush + VAPID
        return PushSubscription.objects.filter(user=user).exists()

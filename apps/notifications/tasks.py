"""Tâches Celery — rappels push quotidiens."""
from celery import shared_task

from apps.notifications.services import PushNotificationService
from apps.users.models import User


@shared_task
def send_daily_question_reminders():
    """Rappel quotidien à tous les utilisateurs abonnés push."""
    sent = 0
    for user in User.objects.filter(is_active=True):
        if PushNotificationService.send_daily_reminder(user):
            sent += 1
    return sent

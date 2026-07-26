"""Contexte global gamification."""
from django.conf import settings

from apps.couples.services import CoupleService
from apps.payments.services import UsageLimitService


def gamification(request):
    """Expose streak et quota couple partagé au template."""
    if not request.user.is_authenticated:
        return {}
    couple = CoupleService.get_active_couple(request.user)
    usage = UsageLimitService.get_usage_summary(request.user)
    from apps.payments.services import SubscriptionService

    monetization = SubscriptionService.get_monetization_context(couple) if couple else {}
    return {
        "active_couple": couple,
        "usage_summary": usage,
        "access": monetization.get("access", {}),
        "free_daily_questions": settings.FREE_DAILY_QUESTIONS,
        "premium_monthly_price": settings.PREMIUM_MONTHLY_PRICE,
        "weekly_price": SubscriptionService.weekly_price(),
        "weekend_price": SubscriptionService.weekend_price(),
        "premium_currency": settings.PREMIUM_CURRENCY,
    }

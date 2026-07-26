"""Services quota couple — délègue l'accès à SubscriptionService."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.couples.models import Couple
from apps.couples.services import CoupleService
from apps.payments.models import CoupleDailyUsage
from apps.payments.services.subscription_service import SubscriptionService


class UsageLimitService:
    """Quota quotidien + intégration plans (weekly / weekend / ads)."""

    @staticmethod
    def _today():
        return timezone.localdate()

    @staticmethod
    def get_couple(user) -> Couple | None:
        return CoupleService.get_active_couple(user)

    @staticmethod
    def _get_or_create_usage(couple: Couple) -> CoupleDailyUsage:
        return CoupleDailyUsage.objects.get_or_create(
            couple=couple,
            date=UsageLimitService._today(),
        )[0]

    @staticmethod
    def get_quota_snapshot(couple: Couple) -> dict:
        """Compteurs bruts sans logique de plan."""
        usage = UsageLimitService._get_or_create_usage(couple)
        base = settings.FREE_DAILY_QUESTIONS
        limit = base + usage.extra_questions
        used = usage.questions_played
        remaining = max(0, limit - used)
        return {
            "limit": limit,
            "base_limit": base,
            "used": used,
            "remaining": remaining,
            "extra_questions": usage.extra_questions,
        }

    @staticmethod
    def is_premium(couple: Couple) -> bool:
        """True si accès illimité (weekly ou weekend actif)."""
        return SubscriptionService.has_unlimited_access(couple)

    @staticmethod
    def daily_base_limit(couple: Couple) -> int:
        if SubscriptionService.has_unlimited_access(couple):
            return 9999
        return settings.FREE_DAILY_QUESTIONS

    @staticmethod
    def effective_limit(couple: Couple) -> int:
        usage = UsageLimitService._get_or_create_usage(couple)
        return UsageLimitService.daily_base_limit(couple) + usage.extra_questions

    @staticmethod
    def questions_used(couple: Couple) -> int:
        return UsageLimitService._get_or_create_usage(couple).questions_played

    @staticmethod
    def can_play(couple: Couple) -> bool:
        """Peut lancer ou continuer une question."""
        access = SubscriptionService.can_access_questions(couple)
        return access["allowed"]

    @staticmethod
    @transaction.atomic
    def increment(couple: Couple) -> None:
        """Consomme une question — ignoré si illimité."""
        if SubscriptionService.has_unlimited_access(couple):
            return
        usage = CoupleDailyUsage.objects.select_for_update().get_or_create(
            couple=couple,
            date=UsageLimitService._today(),
        )[0]
        usage.questions_played += 1
        usage.save(update_fields=["questions_played"])

    @staticmethod
    def get_usage_summary(user) -> dict:
        couple = UsageLimitService.get_couple(user)
        if not couple:
            return {
                "limit": settings.FREE_DAILY_QUESTIONS,
                "base_limit": settings.FREE_DAILY_QUESTIONS,
                "used": 0,
                "remaining": settings.FREE_DAILY_QUESTIONS,
                "extra_questions": 0,
                "is_premium": False,
                "has_couple": False,
                "mode": SubscriptionService.MODE_FREE,
                "unlimited": False,
                "show_paywall": False,
                "badge": "",
            }
        return UsageLimitService.get_usage_summary_for_couple(couple)

    @staticmethod
    def get_usage_summary_for_couple(couple: Couple) -> dict:
        """Résumé complet pour WebSocket et templates."""
        access = SubscriptionService.can_access_questions(couple)
        summary = {
            "has_couple": True,
            "is_premium": access.get("unlimited", False),
            "mode": access.get("mode", SubscriptionService.MODE_FREE),
            "unlimited": access.get("unlimited", False),
            "show_paywall": access.get("show_paywall", False),
            "show_ads": access.get("show_ads", False),
            "all_categories": access.get("all_categories", False),
            "badge": access.get("badge", ""),
            "plan_type": access.get("plan_type", "none"),
            "allowed": access.get("allowed", False),
        }
        if access.get("unlimited"):
            summary.update(
                {
                    "limit": 9999,
                    "base_limit": settings.FREE_DAILY_QUESTIONS,
                    "used": access.get("used", 0),
                    "remaining": 9999,
                    "extra_questions": access.get("extra_questions", 0),
                }
            )
        else:
            summary.update(
                {
                    "limit": access.get("limit", settings.FREE_DAILY_QUESTIONS),
                    "base_limit": access.get("base_limit", settings.FREE_DAILY_QUESTIONS),
                    "used": access.get("used", 0),
                    "remaining": access.get("remaining", 0),
                    "extra_questions": access.get("extra_questions", 0),
                }
            )
        if access.get("weekend_pass_pending"):
            summary["weekend_pass_pending"] = True
            summary["weekend_starts"] = access.get("weekend_starts", "")
        if access.get("weekend_active"):
            summary["weekend_active"] = True
        if access.get("end_date"):
            summary["subscription_end"] = access["end_date"]
        return summary

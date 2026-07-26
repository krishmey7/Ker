"""
Abonnements couple — weekly premium, pass weekend, priorité des plans.
Point central : can_access_questions(couple).
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.couples.models import Couple
from apps.payments.models import PaymentStatus, PaymentTransaction, PlanType, Subscription

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Gestion des plans, accès aux questions et activation sécurisée."""

    MODE_FREE = "free"
    MODE_ADS = "ads"
    MODE_WEEKLY = "weekly"
    MODE_WEEKEND = "weekend"

    @staticmethod
    def weekly_price() -> Decimal:
        return Decimal(str(getattr(settings, "WEEKLY_PREMIUM_PRICE", "1.99")))

    @staticmethod
    def weekend_price() -> Decimal:
        return Decimal(str(getattr(settings, "WEEKEND_PASS_PRICE", "0.50")))

    @staticmethod
    def weekly_duration_days() -> int:
        return getattr(settings, "WEEKLY_PREMIUM_DAYS", 7)

    @staticmethod
    def is_weekend_window(dt: datetime | None = None) -> bool:
        """True entre samedi 00:00 et dimanche 23:59 (fuseau serveur)."""
        local = timezone.localtime(dt or timezone.now())
        return local.weekday() in (5, 6)

    @staticmethod
    def end_of_weekend_period(from_dt: datetime | None = None) -> datetime:
        """Fin de la période weekend (dimanche 23:59:59)."""
        local = timezone.localtime(from_dt or timezone.now())
        weekday = local.weekday()
        if weekday == 6:
            sunday = local.date()
        elif weekday == 5:
            sunday = local.date() + timedelta(days=1)
        else:
            days_ahead = 6 - weekday
            sunday = local.date() + timedelta(days=days_ahead)
        end_naive = datetime.combine(sunday, time(23, 59, 59))
        if timezone.is_aware(local):
            return timezone.make_aware(end_naive, timezone.get_current_timezone())
        return end_naive

    @staticmethod
    def get_subscription(couple: Couple) -> Subscription:
        """Récupère ou crée l'abonnement couple et synchronise l'état."""
        sub, _ = Subscription.objects.get_or_create(
            couple=couple,
            defaults={
                "plan_type": PlanType.NONE,
                "is_active": False,
                "status": "free",
            },
        )
        return SubscriptionService.sync_subscription_state(sub)

    @staticmethod
    @transaction.atomic
    def sync_subscription_state(sub: Subscription) -> Subscription:
        """Expire les abonnements dépassés — désactivation automatique lundi pour weekend."""
        sub = Subscription.objects.select_for_update().get(pk=sub.pk)
        now = timezone.now()
        changed = False

        if sub.is_active and sub.end_date and sub.end_date < now:
            sub.is_active = False
            sub.plan_type = PlanType.NONE
            sub.status = "expired"
            changed = True

        if (
            sub.plan_type == PlanType.WEEKEND
            and sub.is_active
            and sub.end_date
            and sub.end_date < now
        ):
            sub.is_active = False
            sub.plan_type = PlanType.NONE
            sub.status = "expired"
            changed = True

        if changed:
            sub.save(
                update_fields=["is_active", "plan_type", "status", "end_date", "expires_at"]
            )
        return sub

    @staticmethod
    def is_weekly_active(sub: Subscription) -> bool:
        """Premium hebdomadaire actif — priorité absolue."""
        now = timezone.now()
        if not sub.is_active or sub.plan_type != PlanType.WEEKLY:
            return False
        return bool(sub.end_date and sub.end_date >= now)

    @staticmethod
    def is_weekend_unlimited(sub: Subscription) -> bool:
        """Pass weekend actif ET dans la fenêtre samedi–dimanche."""
        now = timezone.now()
        if not sub.is_active or sub.plan_type != PlanType.WEEKEND:
            return False
        if not sub.end_date or sub.end_date < now:
            return False
        return SubscriptionService.is_weekend_window(now)

    @staticmethod
    def has_weekend_pass_pending(sub: Subscription) -> bool:
        """Pass acheté mais hors weekend — quota gratuit jusqu'à samedi."""
        now = timezone.now()
        return (
            sub.is_active
            and sub.plan_type == PlanType.WEEKEND
            and bool(sub.end_date and sub.end_date >= now)
            and not SubscriptionService.is_weekend_window(now)
        )

    @staticmethod
    def can_access_questions(couple: Couple) -> dict:
        """
        Détermine si le couple peut jouer et sous quel mode.

        Priorité : weekly > weekend (fenêtre) > gratuit > ads.
        """
        from apps.payments.services.usage_service import UsageLimitService

        sub = SubscriptionService.get_subscription(couple)
        usage = UsageLimitService.get_quota_snapshot(couple)

        if SubscriptionService.is_weekly_active(sub):
            return {
                "allowed": True,
                "mode": SubscriptionService.MODE_WEEKLY,
                "unlimited": True,
                "show_paywall": False,
                "show_ads": False,
                "all_categories": True,
                "badge": "Illimité ❤️",
                "plan_type": PlanType.WEEKLY,
                "end_date": sub.end_date.isoformat() if sub.end_date else None,
                **usage,
            }

        if SubscriptionService.is_weekend_unlimited(sub):
            return {
                "allowed": True,
                "mode": SubscriptionService.MODE_WEEKEND,
                "unlimited": True,
                "show_paywall": False,
                "show_ads": False,
                "all_categories": True,
                "badge": "Weekend Unlimited 🔥",
                "plan_type": PlanType.WEEKEND,
                "end_date": sub.end_date.isoformat() if sub.end_date else None,
                "weekend_active": True,
                **usage,
            }

        if SubscriptionService.has_weekend_pass_pending(sub):
            usage["weekend_pass_pending"] = True
            usage["weekend_starts"] = SubscriptionService._next_saturday_label()

        if usage["remaining"] > 0:
            return {
                "allowed": True,
                "mode": SubscriptionService.MODE_FREE,
                "unlimited": False,
                "show_paywall": False,
                "show_ads": False,
                "all_categories": False,
                "badge": "",
                "plan_type": PlanType.NONE,
                **usage,
            }

        return {
            "allowed": False,
            "mode": SubscriptionService.MODE_ADS,
            "unlimited": False,
            "show_paywall": True,
            "show_ads": True,
            "all_categories": False,
            "badge": "",
            "plan_type": PlanType.NONE,
            **usage,
        }

    @staticmethod
    def _next_saturday_label() -> str:
        """Libellé court pour le prochain samedi."""
        now = timezone.localtime()
        days = (5 - now.weekday()) % 7
        if days == 0 and now.weekday() != 5:
            days = 7
        target = now.date() + timedelta(days=days)
        return target.strftime("%d/%m")

    @staticmethod
    def has_unlimited_access(couple: Couple) -> bool:
        """True si weekly ou weekend illimité actif."""
        access = SubscriptionService.can_access_questions(couple)
        return access.get("unlimited", False)

    @staticmethod
    @transaction.atomic
    def _apply_weekly_plan(couple: Couple, user, *, external_id: str = "") -> Subscription:
        """Active le plan hebdomadaire sur la subscription (sans créer de paiement)."""
        if SubscriptionService.is_weekly_active(
            SubscriptionService.get_subscription(couple)
        ):
            raise ValueError("Un abonnement hebdomadaire est déjà actif.")

        sub, _ = Subscription.objects.select_for_update().get_or_create(
            couple=couple,
            defaults={"plan_type": PlanType.NONE, "is_active": False, "status": "free"},
        )
        now = timezone.now()
        end = now + timedelta(days=SubscriptionService.weekly_duration_days())

        sub.plan_type = PlanType.WEEKLY
        sub.is_active = True
        sub.start_date = now
        sub.end_date = end
        sub.started_at = now
        sub.expires_at = end
        sub.status = "premium"
        sub.auto_renew = False
        sub.external_id = external_id[:128]
        sub.save()

        SubscriptionService._broadcast_activation(couple, "premium_active", sub)
        logger.info("Weekly premium activated couple=%s", couple.pk)
        return sub

    @staticmethod
    @transaction.atomic
    def activate_weekly(couple: Couple, user, *, external_id: str = "") -> Subscription:
        """Active le premium hebdomadaire (stub — trace paiement complété)."""
        import uuid

        from apps.payments.models import PaymentProvider

        sub = SubscriptionService._apply_weekly_plan(couple, user, external_id=external_id)
        now = timezone.now()
        PaymentTransaction.objects.create(
            couple=couple,
            user=user,
            plan_type=PlanType.WEEKLY,
            status=PaymentStatus.COMPLETED,
            amount=SubscriptionService.weekly_price(),
            currency=getattr(settings, "PREMIUM_CURRENCY", "USD"),
            provider=PaymentProvider.STUB,
            external_reference=f"stub-weekly-{couple.pk}-{uuid.uuid4().hex[:10]}",
            external_id=external_id[:128] or "stub_weekly",
            completed_at=now,
        )
        return sub

    @staticmethod
    @transaction.atomic
    def _apply_weekend_plan(couple: Couple, user, *, external_id: str = "") -> Subscription:
        """Active le pass weekend sur la subscription (sans créer de paiement)."""
        sub, _ = Subscription.objects.select_for_update().get_or_create(
            couple=couple,
            defaults={"plan_type": PlanType.NONE, "is_active": False, "status": "free"},
        )
        sub = SubscriptionService.sync_subscription_state(sub)

        if SubscriptionService.is_weekly_active(sub):
            raise ValueError("Le premium hebdomadaire est déjà actif.")

        if (
            sub.plan_type == PlanType.WEEKEND
            and sub.is_active
            and sub.end_date
            and sub.end_date >= timezone.now()
        ):
            raise ValueError("Un pass weekend est déjà actif pour ce couple.")

        now = timezone.now()
        end = SubscriptionService.end_of_weekend_period(now)

        sub.plan_type = PlanType.WEEKEND
        sub.is_active = True
        sub.start_date = now
        sub.end_date = end
        sub.started_at = now
        sub.expires_at = end
        sub.status = "premium"
        sub.auto_renew = False
        sub.external_id = external_id[:128]
        sub.save()

        event = (
            "weekend_mode_active"
            if SubscriptionService.is_weekend_window(now)
            else "subscription_activated"
        )
        SubscriptionService._broadcast_activation(couple, event, sub)
        logger.info("Weekend pass activated couple=%s until %s", couple.pk, end)
        return sub

    @staticmethod
    @transaction.atomic
    def activate_weekend(couple: Couple, user, *, external_id: str = "") -> Subscription:
        """Active le pass weekend (stub — trace paiement complété)."""
        import uuid

        from apps.payments.models import PaymentProvider

        sub = SubscriptionService._apply_weekend_plan(couple, user, external_id=external_id)
        now = timezone.now()
        PaymentTransaction.objects.create(
            couple=couple,
            user=user,
            plan_type=PlanType.WEEKEND,
            status=PaymentStatus.COMPLETED,
            amount=SubscriptionService.weekend_price(),
            currency=getattr(settings, "PREMIUM_CURRENCY", "USD"),
            provider=PaymentProvider.STUB,
            external_reference=f"stub-weekend-{couple.pk}-{uuid.uuid4().hex[:10]}",
            external_id=external_id[:128] or "stub_weekend",
            completed_at=now,
        )
        return sub

    @staticmethod
    def _broadcast_activation(couple: Couple, event_type: str, sub: Subscription) -> None:
        """Diffuse l'activation d'abonnement via WebSocket."""
        from apps.payments.services.usage_service import UsageLimitService

        access = SubscriptionService.can_access_questions(couple)
        usage = UsageLimitService.get_usage_summary_for_couple(couple)
        payload = {
            "plan_type": sub.plan_type,
            "is_active": sub.is_active,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "access": access,
            "usage": usage,
            "message": access.get("badge", "Abonnement activé ❤️"),
        }
        SubscriptionService.broadcast_room(couple.room_code, {"type": event_type, "payload": payload})
        SubscriptionService.broadcast_room(
            couple.room_code,
            {"type": "subscription_activated", "payload": payload},
        )

    @staticmethod
    def broadcast_room(room_code: str, event: dict) -> None:
        """Envoie un événement à la room couple."""
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"couple_{room_code.upper()}",
                {"type": "room.event", "data": event},
            )
        except Exception as exc:
            logger.warning("Broadcast subscription %s failed: %s", room_code, exc)

    @staticmethod
    def get_monetization_context(couple: Couple | None) -> dict:
        """Contexte template — offres et état d'accès."""
        if not couple:
            return {}
        access = SubscriptionService.can_access_questions(couple)
        return {
            "access": access,
            "weekly_price": SubscriptionService.weekly_price(),
            "weekend_price": SubscriptionService.weekend_price(),
            "is_weekend_window": SubscriptionService.is_weekend_window(),
        }

    # Rétrocompatibilité stub mensuel
    @staticmethod
    @transaction.atomic
    def activate_premium(couple, months: int = 1) -> Subscription:
        """Alias legacy — active le plan hebdomadaire."""
        return SubscriptionService.activate_weekly(couple, couple.user1)

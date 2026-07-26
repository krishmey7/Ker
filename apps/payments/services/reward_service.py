"""
Publicités récompensées — validation backend et déblocage couple.
Le frontend ne débloque jamais directement : tout passe par ici.
"""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.couples.models import Couple
from apps.payments.models import AdReward, CoupleDailyUsage, RewardType
from apps.payments.services.subscription_service import SubscriptionService
from apps.payments.services.usage_service import UsageLimitService

logger = logging.getLogger(__name__)


class RewardedAdService:
    """Cycle pub à deux — chaque partenaire valide, puis crédits partagés."""

    @staticmethod
    def extra_questions_per_unlock() -> int:
        return getattr(settings, "REWARDED_AD_EXTRA_QUESTIONS", 5)

    @staticmethod
    def max_unlocks_per_day() -> int:
        return getattr(settings, "REWARDED_AD_MAX_UNLOCKS_PER_DAY", 10)

    @staticmethod
    def _today():
        return timezone.localdate()

    @staticmethod
    def _partner_id(couple: Couple, user_id: int) -> int | None:
        if couple.user1_id == user_id:
            return couple.user2_id
        if couple.user2_id == user_id:
            return couple.user1_id
        return None

    @staticmethod
    def _unlocks_today(couple: Couple) -> int:
        """Nombre de déblocages déjà accordés aujourd'hui."""
        return (
            AdReward.objects.filter(
                couple=couple,
                credits_applied=True,
                completed_at__date=RewardedAdService._today(),
            )
            .values("reward_cycle_id")
            .distinct()
            .count()
        )

    @staticmethod
    def get_or_create_cycle_id(couple: Couple) -> uuid.UUID:
        """Retourne un cycle ouvert (moins de 2 validations) ou en crée un."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        open_cycles = (
            AdReward.objects.filter(
                couple=couple,
                credits_applied=False,
                created_at__gte=today_start,
            )
            .values_list("reward_cycle_id", flat=True)
            .distinct()
        )
        for cycle_id in open_cycles:
            completed_users = set(
                AdReward.objects.filter(
                    reward_cycle_id=cycle_id,
                    completed=True,
                ).values_list("user_id", flat=True)
            )
            if len(completed_users) < 2:
                return cycle_id
        return uuid.uuid4()

    @staticmethod
    def get_status(couple: Couple, user_id: int) -> dict:
        """État pub pour l'UI (room + API)."""
        partner_id = RewardedAdService._partner_id(couple, user_id)
        cycle_id = RewardedAdService.get_or_create_cycle_id(couple)

        user_reward = AdReward.objects.filter(
            reward_cycle_id=cycle_id, user_id=user_id
        ).first()
        user_completed = bool(user_reward and user_reward.completed)
        partner_completed = (
            AdReward.objects.filter(reward_cycle_id=cycle_id, completed=True)
            .exclude(user_id=user_id)
            .exists()
        )
        cycle_unlocked = AdReward.objects.filter(
            reward_cycle_id=cycle_id, credits_applied=True
        ).exists()

        return {
            "cycle_id": str(cycle_id),
            "user_completed": user_completed,
            "partner_completed": partner_completed,
            "both_completed": user_completed and partner_completed,
            "waiting_for_partner": user_completed and not partner_completed,
            "cycle_unlocked": cycle_unlocked,
            "can_watch_ad": not user_completed and not cycle_unlocked,
            "extra_questions_per_unlock": RewardedAdService.extra_questions_per_unlock(),
            "unlocks_remaining_today": max(
                0,
                RewardedAdService.max_unlocks_per_day() - RewardedAdService._unlocks_today(couple),
            ),
        }

    @staticmethod
    @transaction.atomic
    def record_completion(user, couple: Couple, ad_network: str = "simulated") -> dict:
        """
        Enregistre la fin de pub pour un utilisateur.
        Déclenche unlock_reward_if_complete si les deux ont validé.
        """
        if not couple.is_complete:
            raise ValueError("Le couple doit être complet.")
        if SubscriptionService.has_unlimited_access(couple):
            raise ValueError("Votre plan actuel inclut déjà l'accès illimité.")
        if RewardedAdService._unlocks_today(couple) >= RewardedAdService.max_unlocks_per_day():
            raise ValueError("Limite de déblocages quotidienne atteinte.")

        cycle_id = RewardedAdService.get_or_create_cycle_id(couple)

        if AdReward.objects.filter(reward_cycle_id=cycle_id, credits_applied=True).exists():
            raise ValueError("Cette récompense a déjà été débloquée.")

        reward, created = AdReward.objects.get_or_create(
            reward_cycle_id=cycle_id,
            user=user,
            defaults={
                "couple": couple,
                "reward_type": RewardType.REWARDED_VIDEO,
                "ad_network": ad_network[:32],
            },
        )

        if reward.completed and reward.credits_applied:
            return RewardedAdService._build_result(
                couple, user, cycle_id, unlocked=False, already_done=True
            )

        if reward.completed and not reward.credits_applied:
            unlock = RewardedAdService.unlock_reward_if_complete(couple, cycle_id)
            if unlock:
                return unlock
            return RewardedAdService._build_result(couple, user, cycle_id, unlocked=False)

        reward.completed = True
        reward.completed_at = timezone.now()
        reward.ad_network = ad_network[:32]
        reward.save(update_fields=["completed", "completed_at", "ad_network"])

        unlock = RewardedAdService.unlock_reward_if_complete(couple, cycle_id)
        if unlock:
            return unlock

        ad_rewards = {}
        if couple.user1_id:
            ad_rewards[str(couple.user1_id)] = RewardedAdService.get_status(couple, couple.user1_id)
        if couple.user2_id:
            ad_rewards[str(couple.user2_id)] = RewardedAdService.get_status(couple, couple.user2_id)
        RewardedAdService.broadcast_room(
            couple.room_code,
            {
                "type": "ad_reward_progress",
                "payload": {
                    "user_id": user.id,
                    "ad_rewards": ad_rewards,
                    "usage": UsageLimitService.get_usage_summary_for_couple(couple),
                },
            },
        )

        return RewardedAdService._build_result(couple, user, cycle_id, unlocked=False)

    @staticmethod
    @transaction.atomic
    def unlock_reward_if_complete(couple: Couple, cycle_id: uuid.UUID) -> dict | None:
        """Ajoute les crédits si les deux partenaires ont validé leur pub."""
        if AdReward.objects.filter(reward_cycle_id=cycle_id, credits_applied=True).exists():
            return None

        required = {couple.user1_id, couple.user2_id}
        completed = set(
            AdReward.objects.filter(
                reward_cycle_id=cycle_id,
                completed=True,
            ).values_list("user_id", flat=True)
        )
        if not required.issubset(completed):
            return None

        usage = CoupleDailyUsage.objects.select_for_update().get_or_create(
            couple=couple,
            date=RewardedAdService._today(),
        )[0]
        extra = RewardedAdService.extra_questions_per_unlock()
        usage.extra_questions += extra
        usage.save(update_fields=["extra_questions"])

        AdReward.objects.filter(reward_cycle_id=cycle_id).update(credits_applied=True)

        usage_summary = UsageLimitService.get_usage_summary_for_couple(couple)
        broadcast = {
            "type": "reward_unlocked",
            "payload": {
                "extra_questions": extra,
                "message": f"❤️ Vous avez débloqué {extra} questions",
                "usage": usage_summary,
            },
        }

        RewardedAdService.broadcast_room(couple.room_code, broadcast)

        resume_broadcast = RewardedAdService._try_resume_session(couple)
        if resume_broadcast:
            RewardedAdService.broadcast_room(couple.room_code, resume_broadcast)

        logger.info("Reward unlocked couple=%s cycle=%s +%s questions", couple.pk, cycle_id, extra)

        return RewardedAdService._build_result(
            couple,
            couple.user1,
            cycle_id,
            unlocked=True,
            broadcast=broadcast,
            resume_broadcast=resume_broadcast,
        )

    @staticmethod
    def _try_resume_session(couple: Couple) -> dict | None:
        """Reprend la partie automatiquement après déblocage."""
        from apps.game.models import SessionStatus
        from apps.game.services.realtime import GameRealtimeService

        from apps.game.models import GameSession

        session = (
            GameSession.objects.filter(couple=couple)
            .exclude(status=SessionStatus.FINISHED)
            .order_by("-started_at")
            .first()
        )
        if not session:
            return None
        if not UsageLimitService.can_play(couple):
            return None

        if session.status == SessionStatus.REVEAL:
            result = GameRealtimeService._advance_from_reveal(session)
            return result.get("broadcast") if result else None

        if session.status in (SessionStatus.QUESTION, SessionStatus.WAITING_REVEAL):
            usage = UsageLimitService.get_usage_summary_for_couple(couple)
            return GameRealtimeService._question_broadcast(session, usage)

        return None

    @staticmethod
    def _build_result(
        couple: Couple,
        user,
        cycle_id: uuid.UUID,
        *,
        unlocked: bool,
        already_done: bool = False,
        broadcast: dict | None = None,
        resume_broadcast: dict | None = None,
    ) -> dict:
        return {
            "success": True,
            "unlocked": unlocked,
            "already_done": already_done,
            "ad_reward": RewardedAdService.get_status(couple, user.id),
            "usage": UsageLimitService.get_usage_summary_for_couple(couple),
            "broadcast": broadcast,
            "resume_broadcast": resume_broadcast,
        }

    @staticmethod
    def broadcast_room(room_code: str, event: dict) -> None:
        """Diffuse un événement WebSocket à la room couple."""
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"couple_{room_code.upper()}",
                {"type": "room.event", "data": event},
            )
        except Exception as exc:
            logger.warning("Broadcast pub room %s failed: %s", room_code, exc)

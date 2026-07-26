"""
Orchestration WebSocket — événements room, sans logique IA directe.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction

from apps.couples.models import Couple
from apps.game.db_utils import retry_on_db_locked
from apps.game.models import Answer, GameMode, GameSession, SessionStatus
from apps.game.services.game_engine import GameEngine
from apps.game.services.session_flow import AnswerService, GameSessionService
from apps.payments.services import RewardedAdService, UsageLimitService

logger = logging.getLogger(__name__)


class GameRealtimeService:
    """Orchestration temps réel — délègue la génération au GameEngine."""

    @staticmethod
    def _active_session(room_code: str) -> GameSession | None:
        couple = Couple.objects.filter(room_code=room_code.upper()).first()
        if not couple:
            return None
        return (
            GameSession.objects.filter(couple=couple)
            .exclude(status=SessionStatus.FINISHED)
            .select_related("couple", "current_question")
            .order_by("-started_at")
            .first()
        )

    @staticmethod
    def _paywall_broadcast(couple: Couple) -> dict:
        """Paywall avec état pub pour chaque partenaire."""
        from apps.payments.services.subscription_service import SubscriptionService

        usage = UsageLimitService.get_usage_summary_for_couple(couple)
        access = SubscriptionService.can_access_questions(couple)
        ad_rewards = {}
        if couple.user1_id:
            ad_rewards[str(couple.user1_id)] = RewardedAdService.get_status(couple, couple.user1_id)
        if couple.user2_id:
            ad_rewards[str(couple.user2_id)] = RewardedAdService.get_status(couple, couple.user2_id)
        return {
            "type": "paywall",
            "payload": {
                "reason": "daily_limit",
                "usage": usage,
                "access": access,
                "ad_rewards": ad_rewards,
            },
        }

    @staticmethod
    def _question_broadcast(session: GameSession, usage: dict | None = None) -> dict:
        """Format événement question pour les deux clients."""
        question = GameSessionService.serialize_question(session)
        payload: dict = {"question": question}
        if usage:
            payload["usage"] = usage
        return {
            "type": "question",
            "question": question,
            "payload": payload,
        }

    @staticmethod
    def _serialize_active_question(session: GameSession) -> dict | None:
        """Question sérialisée ou None si absente / invalide."""
        if not session.current_question_id:
            return None
        data = GameSessionService.serialize_question(session)
        return data if data.get("id") and data.get("text") else None

    @staticmethod
    def _try_recover_question(session: GameSession) -> bool:
        """
        Répare une session bloquée (lobby sans question, question supprimée, etc.).
        Retourne False si la session a été terminée (plus de questions).
        """
        session.refresh_from_db()
        if GameRealtimeService._serialize_active_question(session):
            if session.status == SessionStatus.LOBBY:
                session.status = SessionStatus.QUESTION
                session.save(update_fields=["status"])
            return True

        if session.status == SessionStatus.REVEAL:
            return False

        question = GameEngine.generate_next_question(session.id)
        session.refresh_from_db()
        if question:
            return True

        logger.warning(
            "Session %s terminée — impossible de charger une question (couple %s)",
            session.pk,
            session.couple_id,
        )
        return False

    @staticmethod
    def _no_question_error_broadcast() -> dict:
        return {
            "broadcast": {
                "type": "error",
                "payload": {
                    "message": (
                        "Aucune question disponible. "
                        "Exécutez : python manage.py seed_question_bank"
                    ),
                },
            }
        }

    @staticmethod
    def _answer_flags(session: GameSession, user_id: int) -> dict:
        answered = AnswerService.answered_user_ids(session)
        couple = session.couple
        partner_id = None
        if couple.user1_id == user_id:
            partner_id = couple.user2_id
        elif couple.user2_id == user_id:
            partner_id = couple.user1_id
        return {
            "has_answered": user_id in answered,
            "partner_has_answered": bool(partner_id and partner_id in answered),
        }

    @staticmethod
    def get_room_state(room_code: str, user_id: int) -> dict:
        """État complet pour reconnexion."""
        session = GameRealtimeService._active_session(room_code)
        if not session:
            return {"status": "no_session"}

        if session.status not in (SessionStatus.REVEAL, SessionStatus.FINISHED):
            if not GameRealtimeService._serialize_active_question(session):
                if not GameRealtimeService._try_recover_question(session):
                    session = GameRealtimeService._active_session(room_code)
                    if not session:
                        return {"status": "no_session"}

        flags = GameRealtimeService._answer_flags(session, user_id)
        payload = {
            "session_id": session.id,
            "status": session.status,
            **flags,
        }

        if session.status == SessionStatus.REVEAL and AnswerService.both_answered(session):
            reveal = AnswerService.get_reveal_payload(session)
            reveal["auto_next_seconds"] = getattr(settings, "GAME_AUTO_NEXT_SECONDS", 10)
            payload["reveal"] = reveal
            return payload

        couple = session.couple
        usage = UsageLimitService.get_usage_summary_for_couple(couple)
        payload["usage"] = usage

        if usage.get("show_paywall"):
            paywall = GameRealtimeService._paywall_broadcast(couple)
            payload.update(paywall["payload"])
            payload["status"] = "paywall"
            return payload

        question = GameRealtimeService._serialize_active_question(session)
        if question:
            payload["question"] = question
            if session.status == SessionStatus.LOBBY:
                payload["status"] = SessionStatus.QUESTION
            elif flags["has_answered"] and not flags["partner_has_answered"]:
                payload["status"] = SessionStatus.WAITING_REVEAL
        return payload

    @staticmethod
    def handle_event(room_code: str, user_id: int, event_type: str, payload: dict) -> dict | None:
        """Traite un événement WebSocket et prépare le broadcast."""
        if event_type == "start_session":
            return GameRealtimeService._handle_start_session(room_code, user_id, payload)

        session = GameRealtimeService._active_session(room_code)
        if not session:
            return None

        if event_type == "answer_submitted":
            return GameRealtimeService._handle_answer(session, user_id, payload)
        if event_type == "reaction":
            AnswerService.set_reaction(session, user_id, payload.get("emoji", ""))
            return {
                "broadcast": {
                    "type": "reaction",
                    "payload": {"user_id": user_id, "emoji": payload.get("emoji", "")},
                }
            }
        if event_type == "next_question":
            return GameRealtimeService._advance_from_reveal(session, user_id)
        if event_type == "typing_status":
            return {
                "broadcast": {
                    "type": "typing_status",
                    "payload": {"user_id": user_id, "typing": payload.get("typing", False)},
                }
            }
        return None

    @staticmethod
    def _handle_start_session(room_code: str, user_id: int, payload: dict) -> dict | None:
        """Démarre une nouvelle session ou reprend une session active bloquée."""
        couple = Couple.objects.filter(room_code=room_code.upper()).first()
        if not couple or not couple.is_complete:
            return None
        if not UsageLimitService.can_play(couple):
            return {"broadcast": GameRealtimeService._paywall_broadcast(couple)}

        session = GameRealtimeService._active_session(room_code)
        if session:
            return GameRealtimeService._resume_active_session(couple, session)

        return GameRealtimeService._start_new_session(couple, payload)

    @staticmethod
    def _resume_active_session(couple: Couple, session: GameSession) -> dict | None:
        """Reprend une session en cours (reveal, question active, ou réparation)."""
        if session.status == SessionStatus.REVEAL and AnswerService.both_answered(session):
            reveal = AnswerService.get_reveal_payload(session)
            reveal["auto_next_seconds"] = getattr(settings, "GAME_AUTO_NEXT_SECONDS", 10)
            return {"broadcast": {"type": "reveal", "payload": reveal}}

        if not GameRealtimeService._serialize_active_question(session):
            if not GameRealtimeService._try_recover_question(session):
                return GameRealtimeService._no_question_error_broadcast()
            session.refresh_from_db()
            if not Answer.objects.filter(session=session).exists():
                UsageLimitService.increment(couple)

        usage = UsageLimitService.get_usage_summary_for_couple(couple)
        return {"broadcast": GameRealtimeService._question_broadcast(session, usage)}

    @staticmethod
    def _start_new_session(couple: Couple, payload: dict) -> dict | None:
        session = GameSessionService.start(
            couple,
            game_mode=payload.get("game_mode", GameMode.SECRET_ANSWER),
            category=payload.get("category", ""),
        )
        if not GameRealtimeService._serialize_active_question(session):
            if not GameRealtimeService._try_recover_question(session):
                return GameRealtimeService._no_question_error_broadcast()
            session.refresh_from_db()
        UsageLimitService.increment(couple)
        usage = UsageLimitService.get_usage_summary_for_couple(couple)
        return {"broadcast": GameRealtimeService._question_broadcast(session, usage)}

    @staticmethod
    def _handle_answer(session: GameSession, user_id: int, payload: dict) -> dict | None:
        try:
            AnswerService.submit(
                session,
                user_id,
                payload.get("text", ""),
                payload.get("guess_text", ""),
            )
        except ValueError:
            return None

        session.refresh_from_db()

        if AnswerService.both_answered(session):
            session.status = SessionStatus.REVEAL
            session.save(update_fields=["status"])
            GameEngine.schedule_prefetch(session.id)
            GameEngine.schedule_auto_next(session.id, session.couple.room_code)
            reveal = AnswerService.get_reveal_payload(session)
            reveal["auto_next_seconds"] = getattr(settings, "GAME_AUTO_NEXT_SECONDS", 10)
            return {"broadcast": {"type": "reveal", "payload": reveal}}

        session.status = SessionStatus.WAITING_REVEAL
        session.save(update_fields=["status"])
        return {
            "broadcast": {
                "type": "answer_submitted",
                "payload": {"user_id": user_id},
            }
        }

    @staticmethod
    @retry_on_db_locked()
    def _advance_from_reveal(session: GameSession, user_id: int | None = None) -> dict | None:
        """Passe à la question suivante (manuel ou auto) — idempotent, verrou par session."""
        session = GameSession.objects.select_related("couple", "current_question").get(pk=session.id)
        couple = session.couple

        if session.status == SessionStatus.QUESTION:
            if not GameRealtimeService._serialize_active_question(session):
                GameRealtimeService._try_recover_question(session)
                session.refresh_from_db()
            usage = UsageLimitService.get_usage_summary_for_couple(couple)
            return {"broadcast": GameRealtimeService._question_broadcast(session, usage)}

        if session.status != SessionStatus.REVEAL:
            return None

        if not UsageLimitService.can_play(couple):
            return {"broadcast": GameRealtimeService._paywall_broadcast(couple)}

        index_before = session.current_question_index
        question = GameEngine.generate_next_question(session.id)
        session.refresh_from_db()

        if question and session.current_question_index > index_before:
            UsageLimitService.increment(couple)

        if not question:
            return {"broadcast": {"type": "session_finished", "payload": {}}}

        usage = UsageLimitService.get_usage_summary_for_couple(couple)
        return {"broadcast": GameRealtimeService._question_broadcast(session, usage)}

    @staticmethod
    def broadcast_auto_advance(room_code: str) -> None:
        """Appelé par Celery/timer — diffuse la question suivante si toujours en reveal."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        session = GameRealtimeService._active_session(room_code)
        if not session or session.status != SessionStatus.REVEAL:
            return

        result = GameRealtimeService._advance_from_reveal(session)
        if not result or not result.get("broadcast"):
            return

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"couple_{room_code.upper()}",
            {"type": "room.event", "data": result["broadcast"]},
        )

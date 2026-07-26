"""
Services session — réponses, reveal, sérialisation.
Aucune logique IA ici : déléguée au GameEngine.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.couples.models import Couple
from apps.couples.services import CoupleService
from apps.game.models import Answer, GameMode, GameSession, SessionStatus
from apps.game.services.question_picker import QuestionPickerService

# Rétrocompatibilité imports
__all__ = [
    "QuestionPickerService",
    "GameSessionService",
    "AnswerService",
]


class GameSessionService:
    """Cycle de vie d'une session — orchestration sans appel IA direct."""

    @staticmethod
    @transaction.atomic
    def start(couple: Couple, game_mode: str = GameMode.SECRET_ANSWER, category: str = "") -> GameSession:
        """Démarre une session et charge la première question via le moteur."""
        from apps.game.services.game_engine import GameEngine

        session = GameSession.objects.create(
            couple=couple,
            game_mode=game_mode,
            category_filter=category,
            status=SessionStatus.LOBBY,
        )
        CoupleService.update_streak(couple)
        GameEngine.generate_next_question(session.id)
        session.refresh_from_db()
        return session

    @staticmethod
    def serialize_question(session: GameSession) -> dict:
        """Payload question pour le client WebSocket."""
        q = session.current_question
        if not q:
            return {}
        return {
            "id": q.id,
            "text": q.text,
            "category": q.category,
            "spicy_level": q.spicy_level,
            "index": session.current_question_index,
            "game_mode": session.game_mode,
        }


class AnswerService:
    """Soumission et reveal des réponses."""

    @staticmethod
    @transaction.atomic
    def submit(session: GameSession, user_id: int, text: str, guess_text: str = "") -> Answer:
        """Enregistre la réponse d'un partenaire."""
        allowed = (SessionStatus.QUESTION, SessionStatus.WAITING_REVEAL)
        if session.status not in allowed:
            raise ValueError("Aucune question active.")
        if not session.current_question_id:
            raise ValueError("Question manquante.")
        if not text.strip():
            raise ValueError("Réponse vide.")

        answer, _ = Answer.objects.update_or_create(
            session=session,
            question_id=session.current_question_id,
            user_id=user_id,
            defaults={"text": text.strip(), "guess_text": guess_text.strip()},
        )
        return answer

    @staticmethod
    def answered_user_ids(session: GameSession) -> set[int]:
        """Identifiants des utilisateurs ayant répondu à la question en cours."""
        if not session.current_question_id:
            return set()
        return set(
            Answer.objects.filter(
                session=session,
                question_id=session.current_question_id,
            ).values_list("user_id", flat=True)
        )

    @staticmethod
    def both_answered(session: GameSession) -> bool:
        """True si les deux partenaires distincts ont répondu."""
        if not session.current_question_id:
            return False
        couple = Couple.objects.filter(pk=session.couple_id).first()
        if not couple or not couple.is_complete:
            return False
        answered = AnswerService.answered_user_ids(session)
        return couple.user1_id in answered and couple.user2_id in answered

    @staticmethod
    def get_reveal_payload(session: GameSession) -> dict:
        """Payload reveal — moment UX critique."""
        if not AnswerService.both_answered(session):
            return {}

        answers = (
            Answer.objects.filter(
                session=session,
                question_id=session.current_question_id,
            )
            .select_related("user")
            .order_by("user_id")
        )

        from apps.game.services.compatibility_service import CompatibilityService

        round_obj = CompatibilityService.record_round(session)
        couple = session.couple
        couple.refresh_from_db(fields=["compatibility_score", "level"])

        return {
            "question": GameSessionService.serialize_question(session),
            "answers": [
                {
                    "user_id": a.user_id,
                    "label": a.user.label,
                    "text": a.text,
                    "guess_text": a.guess_text,
                    "reaction": a.reaction,
                }
                for a in answers
            ],
            "compatibility_percent": round_obj.compatibility_percent,
            "compatibility_hint": round_obj.compatibility_insight,
            "couple_compatibility_score": couple.compatibility_score,
            "couple_level": couple.level,
        }

    @staticmethod
    @transaction.atomic
    def set_reaction(session: GameSession, user_id: int, emoji: str) -> None:
        """Enregistre une réaction émotionnelle post-reveal."""
        Answer.objects.filter(
            session=session,
            question_id=session.current_question_id,
            user_id=user_id,
        ).update(reaction=emoji[:32])

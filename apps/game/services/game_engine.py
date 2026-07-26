"""
Moteur de jeu — génération de questions : IA (Groq/Gemini) en priorité, banque en fallback.
"""
from __future__ import annotations

import logging
import random
import threading

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.services import get_ai_service
from apps.ai.services.factory import is_live_ai_configured
from apps.game.models import GameSession, Question, QuestionCategory, SessionStatus
from apps.game.db_utils import retry_on_db_locked, session_generation_lock
from apps.game.services.question_picker import QuestionPickerService
from apps.game.services.question_usage_service import QuestionUsageService

logger = logging.getLogger(__name__)

_MAX_UNIQUE_ATTEMPTS = 5


class GameEngine:
    """Génère et associe les questions à une session active."""

    @staticmethod
    def resolve_category(session: GameSession) -> str:
        """Catégorie cible : filtre session ou tirage aléatoire."""
        if session.category_filter:
            return session.category_filter
        return random.choice([c.value for c in QuestionCategory])

    @staticmethod
    def create_question_for_session(session: GameSession) -> Question | None:
        """
        Résout la prochaine question — fiable en production.

        Ordre :
        1. IA (Groq / Gemini) si configurée
        2. Banque admin (1000 questions)
        3. Urgence (pool minimal)
        """
        if is_live_ai_configured():
            ai_question = GameEngine._try_ai_generation(session)
            if ai_question:
                return ai_question
            logger.warning(
                "IA indisponible pour session %s — repli banque locale",
                session.pk,
            )

        picked = QuestionPickerService.pick(session)
        if picked:
            return picked

        return QuestionPickerService._create_emergency(session)

    @staticmethod
    def _try_ai_generation(session: GameSession) -> Question | None:
        """Tentative Groq/Gemini — jusqu'à 5 variantes uniques."""
        couple = session.couple
        category = GameEngine.resolve_category(session)
        spicy = 1 if category == QuestionCategory.SPICY else 0
        exclude_texts = QuestionUsageService.get_used_question_texts(couple)
        
        # Extraire le contexte du couple pour l'IA adaptative
        couple_context = {
            "relationship_duration": couple.relationship_duration,
            "residence_continent": couple.residence_continent,
            "is_long_distance": couple.is_long_distance,
        }

        for attempt in range(_MAX_UNIQUE_ATTEMPTS):
            try:
                item = get_ai_service().generate_question(
                    category=category,
                    spicy_level=spicy,
                    exclude_texts=exclude_texts,
                    couple_context=couple_context,
                )
                text = (item.get("text") or "").strip()
                if not text or QuestionUsageService.is_text_used(couple, text):
                    if text:
                        exclude_texts = list(exclude_texts) + [text]
                    continue
                return Question.objects.create(
                    text=text,
                    category=item.get("category", category),
                    spicy_level=item.get("spicy_level", spicy),
                    game_mode=session.game_mode,
                    is_ai_generated=True,
                    is_active=True,
                )
            except Exception:
                logger.exception(
                    "Génération IA échouée — session %s (tentative %s)",
                    session.pk,
                    attempt + 1,
                )
                break
        return None

    @staticmethod
    def generate_next_question(session_id: int) -> Question | None:
        """
        Charge la question suivante pour la session.
        Priorité : prefetch valide → IA → banque → urgence.
        Les appels IA/DB lourds sont hors transaction pour limiter les verrous SQLite.
        """
        with session_generation_lock(session_id):
            return GameEngine._generate_next_question_locked(session_id)

    @staticmethod
    @retry_on_db_locked()
    def _generate_next_question_locked(session_id: int) -> Question | None:
        prefetched = GameEngine._take_prefetched_question(session_id)
        if prefetched:
            question = prefetched
        else:
            session = GameSession.objects.select_related("couple").get(pk=session_id)
            question = GameEngine.create_question_for_session(session)

        if not question:
            return GameEngine._finish_session_no_questions(session_id)

        applied = GameEngine._apply_next_question(session_id, question)
        if applied:
            GameEngine.schedule_prefetch(session_id)
        return applied

    @staticmethod
    @transaction.atomic
    def _take_prefetched_question(session_id: int) -> Question | None:
        session = (
            GameSession.objects.select_for_update()
            .select_related("couple", "prefetched_question")
            .get(pk=session_id)
        )
        if session.status == SessionStatus.FINISHED:
            return None
        if not session.prefetched_question_id:
            return None
        candidate = session.prefetched_question
        session.prefetched_question = None
        session.save(update_fields=["prefetched_question"])
        if candidate and QuestionUsageService.is_question_allowed(session.couple, candidate):
            return candidate
        return None

    @staticmethod
    @retry_on_db_locked()
    @transaction.atomic
    def _apply_next_question(session_id: int, question: Question) -> Question | None:
        session = GameSession.objects.select_for_update().get(pk=session_id)
        if session.status == SessionStatus.FINISHED:
            return None
        if session.status == SessionStatus.QUESTION and session.current_question_id:
            return session.current_question
        session.current_question = question
        session.current_question_index += 1
        session.status = SessionStatus.QUESTION
        session.save(
            update_fields=[
                "current_question",
                "current_question_index",
                "status",
            ]
        )
        return question

    @staticmethod
    @retry_on_db_locked()
    @transaction.atomic
    def _finish_session_no_questions(session_id: int) -> None:
        session = GameSession.objects.select_for_update().get(pk=session_id)
        if session.status == SessionStatus.FINISHED:
            return None
        logger.error("Aucune question pour session %s — session terminée", session_id)
        session.status = SessionStatus.FINISHED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])
        return None

    @staticmethod
    def prefetch_next_question(session_id: int) -> int | None:
        """Pré-génère la prochaine question hors chemin critique WebSocket."""
        with session_generation_lock(session_id, wait=False) as acquired:
            if not acquired:
                return None
            return GameEngine._prefetch_next_question_impl(session_id)

    @staticmethod
    def _prefetch_next_question_impl(session_id: int) -> int | None:
        try:
            session = GameSession.objects.select_related("couple").get(pk=session_id)
        except GameSession.DoesNotExist:
            return None

        if session.status == SessionStatus.FINISHED:
            return None
        if session.prefetched_question_id:
            if QuestionUsageService.is_question_allowed(
                session.couple, session.prefetched_question
            ):
                return session.prefetched_question_id
            GameSession.objects.filter(pk=session_id).update(prefetched_question=None)

        question = GameEngine.create_question_for_session(session)
        if question and QuestionUsageService.is_question_allowed(session.couple, question):
            GameSession.objects.filter(pk=session_id).update(prefetched_question=question)
            return question.pk
        return None

    @staticmethod
    def schedule_prefetch(session_id: int) -> None:
        """Lance la pré-génération (Celery si dispo, sinon thread daemon)."""
        try:
            from apps.game.tasks import prefetch_question_task

            prefetch_question_task.delay(session_id)
        except Exception:
            threading.Thread(
                target=GameEngine.prefetch_next_question,
                args=(session_id,),
                daemon=True,
            ).start()

    @staticmethod
    def schedule_auto_next(session_id: int, room_code: str) -> None:
        """Programme le passage automatique à la question suivante après reveal."""
        delay = getattr(settings, "GAME_AUTO_NEXT_SECONDS", 10)

        def _run():
            from apps.game.services.realtime import GameRealtimeService

            GameRealtimeService.broadcast_auto_advance(room_code)

        try:
            from apps.game.tasks import auto_advance_after_reveal_task

            auto_advance_after_reveal_task.apply_async(args=[room_code], countdown=delay)
        except Exception:
            threading.Timer(delay, _run).start()

    # Alias rétrocompat
    create_question_via_ai = create_question_for_session

"""
Sélection de questions — banque fallback, sans doublon par couple.
"""
from __future__ import annotations

import logging
import random

from apps.ai.services.static_data import STATIC_QUESTIONS
from apps.game.models import GameSession, Question
from apps.game.services.question_usage_service import QuestionUsageService

logger = logging.getLogger(__name__)


class QuestionPickerService:
    """Pioche dans la banque admin (1000 questions) puis repli contrôlé."""

    @staticmethod
    def pick(session: GameSession) -> Question | None:
        """
        Choisit une question jamais posée à ce couple.
        1. Banque statique (is_ai_generated=False)
        2. Toute question active
        3. Création d'urgence depuis le mini-pool statique
        """
        couple = session.couple
        used_ids = QuestionUsageService.get_used_question_ids(couple)

        question = QuestionPickerService._pick_from_queryset(
            session, used_ids, bank_only=True
        )
        if question:
            return question

        question = QuestionPickerService._pick_from_queryset(
            session, used_ids, bank_only=False
        )
        if question:
            return question

        return QuestionPickerService._create_emergency(session)

    @staticmethod
    def _pick_from_queryset(
        session: GameSession,
        used_ids: set[int],
        *,
        bank_only: bool,
    ) -> Question | None:
        couple = session.couple
        qs = Question.objects.filter(is_active=True).exclude(id__in=used_ids)
        if bank_only:
            qs = qs.filter(is_ai_generated=False)

        category = (session.category_filter or "").strip()
        if category:
            in_category = qs.filter(category=category)
            picked = QuestionPickerService._first_allowed(couple, in_category)
            if picked:
                return picked

        return QuestionPickerService._first_allowed(couple, qs)

    @staticmethod
    def _first_allowed(couple, qs) -> Question | None:
        """Tire au hasard parmi les 40 premières candidates (perf)."""
        ids = list(qs.order_by("?").values_list("id", flat=True)[:40])
        if not ids:
            return None
        random.shuffle(ids)
        for qid in ids:
            question = Question.objects.filter(pk=qid).first()
            if question and QuestionUsageService.is_question_allowed(couple, question):
                return question
        return None

    @staticmethod
    def _create_emergency(session: GameSession) -> Question | None:
        """
        Dernier recours — persiste une question du pool minimal si la banque est vide.
        Garantit qu'une session ne démarre jamais sans question.
        """
        couple = session.couple
        category = session.category_filter or "romantic"
        pool = [q for q in STATIC_QUESTIONS if q.get("category") == category] or STATIC_QUESTIONS
        candidates = list(pool)
        random.shuffle(candidates)

        for item in candidates:
            text = (item.get("text") or "").strip()
            if not text or QuestionUsageService.is_text_used(couple, text):
                continue
            logger.warning("Question d'urgence créée pour couple %s (banque vide ?)", couple.pk)
            return Question.objects.create(
                text=text,
                category=item.get("category", category),
                spicy_level=item.get("spicy_level", 0),
                game_mode=session.game_mode,
                is_ai_generated=False,
                is_active=True,
            )

        text = "Qu'est-ce qui vous fait vous sentir proches l'un de l'autre en ce moment ?"
        if QuestionUsageService.is_text_used(couple, text):
            text = f"{text} (#{session.pk})"
        logger.error("Banque vide — question générique pour couple %s", couple.pk)
        return Question.objects.create(
            text=text,
            category=category,
            spicy_level=0,
            game_mode=session.game_mode,
            is_ai_generated=False,
            is_active=True,
        )

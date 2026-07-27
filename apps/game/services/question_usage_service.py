"""
Suivi des questions déjà posées — évite les doublons pour un couple.
"""
from __future__ import annotations

import re

from apps.couples.models import Couple
from apps.game.models import Answer, GameSession, Question, QuestionRound, SessionStatus


class QuestionUsageService:
    """Identifie les questions déjà vues par un couple."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalise un libellé pour comparaison (casse, espaces)."""
        cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
        return cleaned

    @staticmethod
    def get_used_question_ids(couple: Couple) -> set[int]:
        """Identifiants des questions déjà jouées ou réservées."""
        ids: set[int] = set()

        ids.update(
            Answer.objects.filter(session__couple=couple).values_list("question_id", flat=True)
        )
        ids.update(
            QuestionRound.objects.filter(couple=couple).values_list("question_id", flat=True)
        )
        # Questions actuellement affichées ou réservées pour le couple
        ids.update(
            GameSession.objects.filter(couple=couple)
            .exclude(current_question_id__isnull=True)
            .values_list("current_question_id", flat=True)
        )
        ids.update(
            GameSession.objects.filter(couple=couple)
            .exclude(prefetched_question_id__isnull=True)
            .values_list("prefetched_question_id", flat=True)
        )
        ids.discard(None)
        return ids

    @staticmethod
    def get_used_question_texts(couple: Couple, limit: int = 100) -> list[str]:
        """Textes des questions déjà posées (pour le prompt IA)."""
        used_ids = QuestionUsageService.get_used_question_ids(couple)
        if not used_ids:
            return []
        texts = list(
            Question.objects.filter(id__in=used_ids)
            .order_by("-id")
            .values_list("text", flat=True)[:limit]
        )
        return texts

    @staticmethod
    def is_text_used(couple: Couple, text: str) -> bool:
        """True si une question identique a déjà été posée au couple."""
        normalized = QuestionUsageService.normalize_text(text)
        if not normalized:
            return True
        used_ids = QuestionUsageService.get_used_question_ids(couple)
        for q_text in Question.objects.filter(id__in=used_ids).values_list("text", flat=True):
            if QuestionUsageService.normalize_text(q_text) == normalized:
                return True
        return False

    @staticmethod
    def is_question_allowed(couple: Couple, question: Question | None) -> bool:
        """Vérifie qu'une question n'a pas déjà été utilisée."""
        if not question:
            return False
        if question.id in QuestionUsageService.get_used_question_ids(couple):
            return False
        return not QuestionUsageService.is_text_used(couple, question.text)

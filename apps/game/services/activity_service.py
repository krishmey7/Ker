"""
Activités couple — suggestions Gemini selon compatibilité et niveau.
"""
from __future__ import annotations

from apps.ai.services import get_ai_service
from apps.couples.models import Couple
from apps.game.models import QuestionRound


class CoupleActivityService:
    """Propose une activité personnalisée via l'IA."""

    @staticmethod
    def recent_topics(couple: Couple, limit: int = 5) -> list[str]:
        """Dernières questions jouées pour contextualiser l'activité."""
        return list(
            QuestionRound.objects.filter(couple=couple)
            .select_related("question")
            .order_by("-played_at")[:limit]
            .values_list("question__text", flat=True)
        )

    @staticmethod
    def suggest_activity(couple: Couple) -> dict:
        """Génère une activité adaptée au couple (appel Gemini)."""
        topics = CoupleActivityService.recent_topics(couple)
        return get_ai_service().suggest_couple_activity(
            compatibility_score=couple.compatibility_score,
            level=couple.level,
            recent_topics=topics,
        )

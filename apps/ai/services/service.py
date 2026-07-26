"""
Service IA principal — point d'entrée métier.
Aucun appel API dans les views : tout passe par ici.
"""
from __future__ import annotations

import logging

from django.db import transaction

from apps.ai.services.factory import get_provider
from apps.ai.services.prompts import normalize_category
from apps.game.models import Question

logger = logging.getLogger(__name__)


class AIService:
    """Façade haut niveau pour génération de contenu couple."""

    def __init__(self, provider=None):
        self._provider = provider or get_provider()

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def generate_text(self, prompt: str) -> str:
        """Texte libre via le provider actif."""
        return self._provider.generate_text(prompt)

    def generate_question(
        self,
        category: str = "romantic",
        spicy_level: int = 0,
        exclude_texts: list[str] | None = None,
        couple_context: dict | None = None,
    ) -> dict:
        """
        Génère une question de couple.

        Exemple :
            ai_service.generate_question(category="romantique")
        
        Args:
            couple_context: dict avec 'relationship_duration', 'residence_continent', 'is_long_distance'
        """
        cat = normalize_category(category)
        
        # Transmettre le contexte du couple au provider si supporté
        if couple_context and hasattr(self._provider, 'set_couple_context'):
            self._provider.set_couple_context(couple_context)
        
        items = self._provider.generate_questions(
            cat, count=1, spicy_level=spicy_level, exclude_texts=exclude_texts
        )
        if items:
            return items[0]
        return {
            "text": "Qu'est-ce qui te fait te sentir aimé·e dans notre relation ?",
            "category": cat,
            "spicy_level": spicy_level,
        }

    def generate_questions(
        self,
        category: str,
        count: int = 5,
        spicy_level: int = 0,
        exclude_texts: list[str] | None = None,
    ) -> list[dict]:
        """Génère plusieurs questions (batch, ex. Celery)."""
        cat = normalize_category(category)
        return self._provider.generate_questions(cat, count, spicy_level, exclude_texts)

    def generate_emotional_phrase(self, context: str = "") -> str:
        """Phrase émotionnelle courte pour l'UI."""
        return self._provider.generate_emotional_phrase(context)

    def compatibility_summary(self, answers_context: list[dict]) -> str:
        """Insight relationnel après une session."""
        return self._provider.compatibility_summary(answers_context)

    def calculate_compatibility_score(
        self, question_text: str, answers_context: list[dict]
    ) -> dict:
        """
        Score 0-100 — moteur déterministe + enrichissement IA optionnel.
        Préférer CompatibilityService.compute_round_result() côté jeu.
        """
        from apps.game.services.compatibility_service import CompatibilityService

        if not answers_context:
            return {"percent": 50, "insight": ""}
        return CompatibilityService.compute_round_result(question_text, answers_context)

    def enrich_compatibility_insight(
        self,
        question_text: str,
        answers_context: list[dict],
        percent: int,
        insight_local: str,
        matched_themes: list[str] | None = None,
    ) -> tuple[str, bool]:
        """Enrichissement narratif uniquement — le score est déjà fixé."""
        from apps.ai.services.relationship_ai import RelationshipAI

        return RelationshipAI().enrich(
            question_text,
            answers_context,
            percent=percent,
            insight_local=insight_local,
            matched_themes=matched_themes,
        )

    def suggest_couple_activity(
        self,
        compatibility_score: int,
        level: int,
        recent_topics: list[str] | None = None,
    ) -> dict:
        """Propose une activité de couple selon le profil du duo."""
        return self._provider.suggest_couple_activity(
            compatibility_score,
            level,
            recent_topics or [],
        )


class QuestionBatchService:
    """Persiste des questions générées en base (batch, pas temps réel)."""

    @staticmethod
    @transaction.atomic
    def generate_and_store(
        category: str,
        count: int = 20,
        spicy_level: int = 0,
        service: AIService | None = None,
    ) -> int:
        """Génère et enregistre des questions via le service IA."""
        ai = service or get_ai_service()
        items = ai.generate_questions(category, count, spicy_level)
        created = 0
        for item in items:
            _, was_created = Question.objects.get_or_create(
                text=item["text"],
                category=item.get("category", normalize_category(category)),
                defaults={
                    "spicy_level": item.get("spicy_level", spicy_level),
                    "is_ai_generated": True,
                },
            )
            if was_created:
                created += 1
        logger.info("Batch %s: %s questions créées (%s)", category, created, ai.provider_name)
        return created


_default_service: AIService | None = None


def get_ai_service() -> AIService:
    """Singleton du service IA."""
    global _default_service
    if _default_service is None:
        _default_service = AIService()
    return _default_service

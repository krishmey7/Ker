"""
IA relationnelle — enrichissement narratif uniquement (jamais le score final).
"""
from __future__ import annotations

import logging
import random

from apps.ai.services.exceptions import AIProviderError
from apps.ai.services.factory import get_provider, is_live_provider
from apps.ai.services.prompts import compatibility_enrichment_prompt

logger = logging.getLogger(__name__)

UNAVAILABLE_SUFFIX = "Analyse personnalisée indisponible pour l'instant. ❤️"


class RelationshipAI:
    """
    Enrichit l'insight après calcul déterministe.
    Le pourcentage est fixé en amont — l'IA ne peut pas le modifier.
    """

    def enrich(
        self,
        question_text: str,
        answers_context: list[dict],
        *,
        percent: int,
        insight_local: str,
        matched_themes: list[str] | None = None,
    ) -> tuple[str, bool]:
        """
        Retourne (insight_affiché, ia_utilisée).

        :returns: texte pour l'UI + True si l'appel IA a réussi
        """
        local = insight_local
        themes = matched_themes or []

        try:
            provider = get_provider()
            if not is_live_provider(provider):
                return self._fallback_insight(local, percent), False

            prompt = compatibility_enrichment_prompt(
                question_text=question_text,
                answers_context=answers_context,
                percent=percent,
                matched_themes=themes,
                local_summary=local,
            )
            raw = provider.generate_text(prompt).strip()
            insight = self._sanitize_insight(raw, local)
            if insight:
                return insight, True
        except (AIProviderError, ValueError, TypeError, OSError) as exc:
            logger.warning("RelationshipAI enrich failed, using local: %s", exc)

        return self._fallback_insight(local, percent), False

    @staticmethod
    def _sanitize_insight(raw: str, local_fallback: str) -> str:
        """Nettoie la réponse IA — pas de JSON, longueur limitée."""
        text = raw.strip()
        if text.startswith("{") or text.startswith("["):
            return ""
        text = text.replace("\n", " ").strip()
        if len(text) < 12:
            return ""
        return text[:300]

    @staticmethod
    def _fallback_insight(insight_local: str, percent: int) -> str:
        """Texte local quand l'IA est indisponible — app stable, score inchangé."""
        from apps.game.services.compatibility_data import FALLBACK_INSIGHTS, FALLBACK_TIPS

        base = insight_local or random.choice(FALLBACK_INSIGHTS)
        if percent >= 80 and "❤️" not in base:
            base = f"{base} ❤️"
        tip = random.choice(FALLBACK_TIPS)
        return f"{base}\n\n{UNAVAILABLE_SUFFIX}\nConseil du jour : {tip}"

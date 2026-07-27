"""
Provider Groq — API OpenAI-compatible (Llama, Mixtral, etc.).
Modèle par défaut : llama-3.3-70b-versatile.
"""
from __future__ import annotations

import logging

from django.conf import settings

from apps.ai.services.base import AIProvider
from apps.ai.services.exceptions import AIProviderError
from apps.ai.services.llm_parsing import parse_json_object, parse_questions_json
from apps.ai.services.prompts import (
    compatibility_prompt,
    couple_activity_prompt,
    emotional_phrase_prompt,
    normalize_category,
    question_prompt,
    single_question_prompt,
)
from apps.ai.services.static_provider import StaticProvider

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Intégration Groq via le SDK officiel groq."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or getattr(settings, "GROQ_API_KEY", "")
        self.model_name = model_name or getattr(
            settings, "GROQ_MODEL", "llama-3.1-8b-instant"
        )
        self.timeout = timeout or getattr(settings, "AI_REQUEST_TIMEOUT", 15)
        self._fallback = StaticProvider()
        self._client = None
        self._couple_context = None

    @property
    def name(self) -> str:
        return "GroqProvider"

    def set_couple_context(self, couple_context: dict | None) -> None:
        """Définit le contexte du couple pour les prompts adaptatifs."""
        self._couple_context = couple_context

    def _get_system_prompt(self) -> str:
        """Génère le prompt système adapté au contexte du couple."""
        from apps.ai.services.prompts import get_adaptive_system_prompt

        if self._couple_context:
            return get_adaptive_system_prompt(self._couple_context)
        return (
            "Tu es un assistant pour un jeu de couple en français. "
            "Réponds de façon concise et respectueuse."
        )

    def _ensure_client(self):
        """Initialise le client Groq une seule fois."""
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise AIProviderError("GROQ_API_KEY manquante.")
        try:
            from groq import Groq

            self._client = Groq(
                api_key=self.api_key,
                timeout=self.timeout,
            )
            return self._client
        except ImportError as exc:
            raise AIProviderError(
                "Package groq non installé. Exécutez : pip install groq"
            ) from exc

    def generate_text(self, prompt: str) -> str:
        """Appel chat completion avec gestion d'erreurs."""
        if not prompt.strip():
            raise AIProviderError("Prompt vide.")
        try:
            client = self._ensure_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.82,
                max_tokens=1024,
            )
            text = response.choices[0].message.content
            if text and str(text).strip():
                return str(text).strip()
            raise AIProviderError("Réponse Groq vide.")
        except AIProviderError:
            raise
        except Exception as exc:
            logger.warning("Groq generate_text failed: %s", exc)
            raise AIProviderError(str(exc)) from exc

    def generate_questions(
        self,
        category: str,
        count: int,
        spicy_level: int = 0,
        exclude_texts: list[str] | None = None,
    ) -> list[dict]:
        """Génère un lot de questions ; fallback statique si échec."""
        cat = normalize_category(category)
        try:
            return self._generate_questions(cat, count, spicy_level, exclude_texts)
        except AIProviderError as exc:
            if self._should_retry_with_fallback_model(exc):
                try:
                    return self._generate_questions(cat, count, spicy_level, exclude_texts)
                except AIProviderError as exc_retry:
                    logger.warning(
                        "Groq questions fallback after retry: %s",
                        exc_retry,
                    )
                    return self._fallback.generate_questions(
                        cat, count, spicy_level, exclude_texts
                    )
            logger.warning("Groq questions fallback: %s", exc)
            return self._fallback.generate_questions(cat, count, spicy_level, exclude_texts)

    def _generate_questions(
        self,
        category: str,
        count: int,
        spicy_level: int = 0,
        exclude_texts: list[str] | None = None,
    ) -> list[dict]:
        prompt = question_prompt(
            category, count=count, spicy_level=spicy_level, exclude_texts=exclude_texts
        )
        raw = self.generate_text(prompt)
        items = parse_questions_json(raw, category, spicy_level)
        if items:
            return items[:count]
        raise AIProviderError("Groq a renvoyé des questions invalides.")

    def _should_retry_with_fallback_model(self, exc: AIProviderError) -> bool:
        text = str(exc).lower()
        if "model_not_found" in text or "does not exist" in text or "do not have access" in text:
            fallback_model = getattr(
                settings, "GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile"
            )
            if fallback_model and fallback_model != self.model_name:
                logger.warning(
                    "Groq model unavailable (%s). Retrying with fallback model %s.",
                    self.model_name,
                    fallback_model,
                )
                self.model_name = fallback_model
                self._client = None
                return True
        return False

    def generate_emotional_phrase(self, context: str = "") -> str:
        try:
            return self.generate_text(emotional_phrase_prompt(context))[:200]
        except AIProviderError:
            return self._fallback.generate_emotional_phrase(context)

    def compatibility_summary(self, answers_context: list[dict]) -> str:
        if not answers_context:
            return self._fallback.compatibility_summary(answers_context)
        try:
            return self.generate_text(compatibility_prompt(answers_context))[:200]
        except AIProviderError:
            return self._fallback.compatibility_summary(answers_context)

    def calculate_compatibility_score(
        self, question_text: str, answers_context: list[dict]
    ) -> dict:
        from apps.game.services.compatibility_service import CompatibilityService

        if not answers_context:
            return self._fallback.calculate_compatibility_score(question_text, answers_context)
        result = CompatibilityService.compute_round_result(question_text, answers_context)
        return {"percent": result["percent"], "insight": result["insight"][:300]}

    def suggest_couple_activity(
        self,
        compatibility_score: int,
        level: int,
        recent_topics: list[str],
    ) -> dict:
        try:
            prompt = couple_activity_prompt(compatibility_score, level, recent_topics)
            raw = self.generate_text(prompt)
            data = parse_json_object(raw)
            return {
                "title": str(data.get("title", "Moment à deux"))[:120],
                "description": str(data.get("description", ""))[:500],
                "duration_minutes": max(10, min(180, int(data.get("duration_minutes", 45)))),
                "tips": str(data.get("tips", ""))[:300],
            }
        except (AIProviderError, ValueError, TypeError) as exc:
            logger.warning("Groq activity fallback: %s", exc)
            return self._fallback.suggest_couple_activity(
                compatibility_score, level, recent_topics
            )

    @staticmethod
    def build_single_question_prompt(category: str, spicy_level: int = 0) -> str:
        return single_question_prompt(normalize_category(category), spicy_level)

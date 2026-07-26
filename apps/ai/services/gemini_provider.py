"""
Provider Google Gemini — SDK google-genai (API officielle).
Modèle par défaut : gemini-2.0-flash.
"""
from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from apps.ai.services.base import AIProvider
from apps.ai.services.exceptions import GeminiAPIError
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


class GeminiProvider(AIProvider):
    """Intégration Gemini via le SDK google-genai."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        self.timeout = timeout or getattr(settings, "AI_REQUEST_TIMEOUT", 30)
        self._fallback = StaticProvider()
        self._client = None

    @property
    def name(self) -> str:
        return "GeminiProvider"

    def _ensure_client(self):
        """Initialise le client google-genai une seule fois."""
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise GeminiAPIError("GEMINI_API_KEY manquante.")
        try:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout * 1000),
            )
            return self._client
        except ImportError as exc:
            raise GeminiAPIError(
                "Package google-genai non installé. Exécutez : pip install google-genai"
            ) from exc

    def _extract_text(self, response) -> str:
        """Extrait le texte de la réponse SDK."""
        text = getattr(response, "text", None)
        if text and str(text).strip():
            return str(text).strip()
        raise GeminiAPIError("Réponse Gemini vide.")

    def generate_text(self, prompt: str) -> str:
        """Appel texte brut avec gestion d'erreurs."""
        if not prompt.strip():
            raise GeminiAPIError("Prompt vide.")
        try:
            client = self._ensure_client()
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return self._extract_text(response)
        except GeminiAPIError:
            raise
        except Exception as exc:
            logger.warning("Gemini generate_text failed: %s", exc)
            raise GeminiAPIError(str(exc)) from exc

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
            prompt = question_prompt(
                cat, count=count, spicy_level=spicy_level, exclude_texts=exclude_texts
            )
            raw = self.generate_text(prompt)
            items = self._parse_questions_json(raw, cat, spicy_level)
            if items:
                return items[:count]
        except GeminiAPIError as exc:
            logger.warning("Gemini questions fallback: %s", exc)
        return self._fallback.generate_questions(cat, count, spicy_level, exclude_texts)

    def generate_emotional_phrase(self, context: str = "") -> str:
        """Phrase courte émotionnelle."""
        try:
            return self.generate_text(emotional_phrase_prompt(context))[:200]
        except GeminiAPIError:
            return self._fallback.generate_emotional_phrase(context)

    def compatibility_summary(self, answers_context: list[dict]) -> str:
        """Résumé relationnel post-reveal."""
        if not answers_context:
            return self._fallback.compatibility_summary(answers_context)
        try:
            return self.generate_text(compatibility_prompt(answers_context))[:200]
        except GeminiAPIError:
            return self._fallback.compatibility_summary(answers_context)

    def calculate_compatibility_score(
        self, question_text: str, answers_context: list[dict]
    ) -> dict:
        """
        Compatibilité hybride — score local, insight IA optionnel.
        Conservé pour l'interface AIProvider ; ne délègue plus le score à Gemini.
        """
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
        """Activité de couple personnalisée via Gemini."""
        try:
            prompt = couple_activity_prompt(compatibility_score, level, recent_topics)
            raw = self.generate_text(prompt)
            data = self._parse_json_object(raw)
            return {
                "title": str(data.get("title", "Moment à deux"))[:120],
                "description": str(data.get("description", ""))[:500],
                "duration_minutes": max(10, min(180, int(data.get("duration_minutes", 45)))),
                "tips": str(data.get("tips", ""))[:300],
            }
        except (GeminiAPIError, ValueError, TypeError) as exc:
            logger.warning("Gemini activity fallback: %s", exc)
            return self._fallback.suggest_couple_activity(
                compatibility_score, level, recent_topics
            )

    @staticmethod
    def _parse_json_object(raw: str) -> dict:
        """Extrait un objet JSON depuis la réponse Gemini."""
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("JSON attendu : objet.")
        return data

    def _parse_questions_json(self, raw: str, category: str, spicy_level: int) -> list[dict]:
        """Extrait le JSON même si Gemini ajoute du markdown."""
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        data = json.loads(cleaned)
        if not isinstance(data, list):
            return []
        results = []
        for item in data:
            if not isinstance(item, dict) or not item.get("text"):
                continue
            results.append(
                {
                    "text": str(item["text"]).strip()[:500],
                    "category": normalize_category(item.get("category", category)),
                    "spicy_level": int(item.get("spicy_level", spicy_level)),
                }
            )
        return results

    @staticmethod
    def build_single_question_prompt(category: str, spicy_level: int = 0) -> str:
        """Expose le prompt unitaire (tests)."""
        return single_question_prompt(normalize_category(category), spicy_level)

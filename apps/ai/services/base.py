"""Classe de base pour tous les providers IA."""
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Interface commune — interchangeable (Gemini, OpenAI, etc.)."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Génère du texte brut à partir d'un prompt."""

    @abstractmethod
    def generate_questions(
        self,
        category: str,
        count: int,
        spicy_level: int = 0,
        exclude_texts: list[str] | None = None,
    ) -> list[dict]:
        """Génère un lot de questions structurées."""

    @abstractmethod
    def generate_emotional_phrase(self, context: str = "") -> str:
        """Génère une phrase émotionnelle courte."""

    @abstractmethod
    def compatibility_summary(self, answers_context: list[dict]) -> str:
        """Résumé de compatibilité à partir des réponses."""

    @abstractmethod
    def calculate_compatibility_score(
        self, question_text: str, answers_context: list[dict]
    ) -> dict:
        """Score 0-100 et insight court : {"percent": int, "insight": str}."""

    @abstractmethod
    def suggest_couple_activity(
        self,
        compatibility_score: int,
        level: int,
        recent_topics: list[str],
    ) -> dict:
        """Activité suggérée : title, description, duration_minutes, tips."""

    @property
    def name(self) -> str:
        """Nom du provider pour les logs."""
        return self.__class__.__name__

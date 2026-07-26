"""Exceptions de la couche IA."""


class AIProviderError(Exception):
    """Erreur générique du provider IA."""


class GeminiAPIError(AIProviderError):
    """Erreur lors d'un appel à l'API Gemini."""

"""Rétrocompatibilité — préférer apps.ai.services."""
from apps.ai.services import AIService, QuestionBatchService, get_ai_service, get_provider

# Alias historique
get_ai_provider = get_provider

__all__ = [
    "AIService",
    "QuestionBatchService",
    "get_ai_service",
    "get_ai_provider",
    "get_provider",
]

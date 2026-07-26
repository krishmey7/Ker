"""Couche services IA — exports publics."""
from apps.ai.services.service import AIService, QuestionBatchService, get_ai_service
from apps.ai.services.factory import get_provider
from apps.ai.services.factory import is_live_ai_configured, is_live_provider
from apps.ai.services.gemini_provider import GeminiProvider
from apps.ai.services.groq_provider import GroqProvider

__all__ = [
    "AIService",
    "RelationshipAI",
    "QuestionBatchService",
    "get_ai_service",
    "get_provider",
    "is_live_ai_configured",
    "is_live_provider",
    "GroqProvider",
    "GeminiProvider",
]

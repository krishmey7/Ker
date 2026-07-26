"""
Point d'entrée IA — alias public vers AIService.
"""
from apps.ai.services.service import AIService, QuestionBatchService, get_ai_service

__all__ = ["AIService", "QuestionBatchService", "get_ai_service"]

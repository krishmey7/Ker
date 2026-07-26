"""Tâches Celery — génération batch IA (hors requête HTTP)."""
from celery import shared_task

from apps.ai.services import QuestionBatchService


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_questions_batch(self, category: str, count: int = 20, spicy_level: int = 0):
    """
    Remplit la banque de questions en arrière-plan.
    Idéal pour ne pas bloquer les requêtes utilisateur.
    """
    try:
        return QuestionBatchService.generate_and_store(
            category=category,
            count=count,
            spicy_level=spicy_level,
        )
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@shared_task
def generate_single_question_task(category: str = "romantic", spicy_level: int = 0):
    """Génère une question et la persiste."""
    from apps.ai.services import get_ai_service

    item = get_ai_service().generate_question(category=category, spicy_level=spicy_level)
    from apps.game.models import Question

    q, created = Question.objects.get_or_create(
        text=item["text"],
        category=item.get("category", category),
        defaults={"spicy_level": item.get("spicy_level", 0), "is_ai_generated": True},
    )
    return {"id": q.id, "created": created, "text": q.text}

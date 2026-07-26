"""Tâches Celery — pré-génération et avancement automatique du jeu."""
from celery import shared_task


@shared_task(ignore_result=True)
def prefetch_question_task(session_id: int) -> int | None:
    """Pré-génère la prochaine question Gemini pendant le reveal."""
    from apps.game.services.game_engine import GameEngine

    return GameEngine.prefetch_next_question(session_id)


@shared_task(ignore_result=True)
def auto_advance_after_reveal_task(room_code: str) -> None:
    """Passe automatiquement à la question suivante et diffuse via WebSocket."""
    from apps.game.services.realtime import GameRealtimeService

    GameRealtimeService.broadcast_auto_advance(room_code)

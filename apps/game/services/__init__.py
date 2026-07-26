"""
Services jeu — exports lazy (évite le cycle ai ↔ game au démarrage).

Usage direct recommandé :
    from apps.game.services.game_engine import GameEngine
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "GameEngine",
    "GameRealtimeService",
    "GameSessionService",
    "AnswerService",
    "QuestionPickerService",
    "CompatibilityEngine",
    "CompatibilityService",
    "CoupleProgressService",
    "CoupleActivityService",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "GameEngine": ("apps.game.services.game_engine", "GameEngine"),
    "GameRealtimeService": ("apps.game.services.realtime", "GameRealtimeService"),
    "GameSessionService": ("apps.game.services.session_flow", "GameSessionService"),
    "AnswerService": ("apps.game.services.session_flow", "AnswerService"),
    "QuestionPickerService": ("apps.game.services.question_picker", "QuestionPickerService"),
    "CompatibilityEngine": ("apps.game.services.compatibility_engine", "CompatibilityEngine"),
    "CompatibilityService": ("apps.game.services.compatibility_service", "CompatibilityService"),
    "CoupleProgressService": ("apps.game.services.couple_progress_service", "CoupleProgressService"),
    "CoupleActivityService": ("apps.game.services.activity_service", "CoupleActivityService"),
}


def __getattr__(name: str) -> Any:
    """Charge un service à la demande."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = _LAZY_EXPORTS[name]
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, attr)

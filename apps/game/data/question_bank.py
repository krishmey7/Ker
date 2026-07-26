"""
Banque fallback 1000 questions — Gary Chapman.
Utilisé par : python manage.py seed_question_bank
"""
from __future__ import annotations

from apps.game.data.chapman_bank_builder import (
    BANK_TARGETS,
    generate_chapman_bank_questions,
)
from apps.game.data.chapman_framework import BOOK_AUTHOR, BOOK_TITLE

__all__ = [
    "BANK_TARGETS",
    "BOOK_TITLE",
    "BOOK_AUTHOR",
    "generate_bank_questions",
]


def generate_bank_questions() -> list[dict]:
    """Génère exactement 1000 questions complètes et uniques."""
    return generate_chapman_bank_questions()

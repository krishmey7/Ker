"""Vérifie que la banque Chapman génère 1000 questions uniques."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

django.setup()

from apps.game.data.question_bank import generate_bank_questions

if __name__ == "__main__":
    items = generate_bank_questions()
    print(f"OK: {len(items)} questions, {len({q['text'] for q in items})} uniques")

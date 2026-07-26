"""
Point d'entrée des données de compatibilité — réexporte thèmes, signaux et fallbacks.
Analyses locales alignées sur Gary Chapman (voir chapman_framework).
"""
from apps.game.data.chapman_framework import (
    CHAPMAN_FALLBACK_INSIGHTS,
    CHAPMAN_FALLBACK_TIPS,
)
from apps.game.services.compatibility_signals import (
    COMPLEMENTARY_PAIRS,
    NEGATIVE_WORDS,
    POLARITY_CONFLICT_MALUS,
    POSITIVE_ALIGNMENT_BONUS,
    POSITIVE_WORDS,
    SHARED_NEGATIVE_BONUS,
    TENSION_PAIRS,
)
from apps.game.services.compatibility_themes import (
    CATEGORY_THEME_BOOST,
    THEME_LABELS,
    THEME_RULES,
)

# Conseils locaux si l'IA est indisponible (Gary Chapman)
FALLBACK_TIPS: list[str] = list(CHAPMAN_FALLBACK_TIPS)

FALLBACK_INSIGHTS: list[str] = list(CHAPMAN_FALLBACK_INSIGHTS)

# Score de départ selon la catégorie de question
CATEGORY_BASELINE: dict[str, int] = {
    "romantic": 52,
    "funny": 54,
    "spicy": 51,
    "deep": 51,
    "know_partner": 53,
    "future": 52,
    "habits": 51,
}

__all__ = [
    "THEME_RULES",
    "THEME_LABELS",
    "CATEGORY_THEME_BOOST",
    "COMPLEMENTARY_PAIRS",
    "TENSION_PAIRS",
    "POSITIVE_WORDS",
    "NEGATIVE_WORDS",
    "POSITIVE_ALIGNMENT_BONUS",
    "POLARITY_CONFLICT_MALUS",
    "SHARED_NEGATIVE_BONUS",
    "FALLBACK_TIPS",
    "FALLBACK_INSIGHTS",
    "CATEGORY_BASELINE",
]

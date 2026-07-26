"""
Moteur de compatibilité déterministe — source de vérité pour le score (0–100).
L'IA n'intervient pas ici ; elle enrichit uniquement le texte via RelationshipAI.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from apps.game.services.compatibility_data import (
    CATEGORY_BASELINE,
    CATEGORY_THEME_BOOST,
    COMPLEMENTARY_PAIRS,
    FALLBACK_INSIGHTS,
    NEGATIVE_WORDS,
    POLARITY_CONFLICT_MALUS,
    POSITIVE_ALIGNMENT_BONUS,
    POSITIVE_WORDS,
    SHARED_NEGATIVE_BONUS,
    TENSION_PAIRS,
    THEME_LABELS,
    THEME_RULES,
)


@dataclass
class CompatibilityEngineResult:
    """Résultat du calcul local — score fiable et texte de secours."""

    percent: int
    insight_local: str
    matched_themes: list[str] = field(default_factory=list)
    exact_match: bool = False
    word_overlap_ratio: float = 0.0
    adjustments: list[str] = field(default_factory=list)


class CompatibilityEngine:
    """
    Calcule la compatibilité à partir des réponses uniquement.
    Règles explicites : similarité, thèmes (45+), polarité, tensions, complémentarité.
    """

    BASELINE = 50
    EXACT_MATCH_BONUS = 22
    MAX_OVERLAP_BONUS = 18
    CATEGORY_THEME_EXTRA = 3
    MIN_PERCENT = 5
    MAX_PERCENT = 98

    @classmethod
    def calculate(
        cls,
        question_text: str,
        answers_context: list[dict],
        category: str = "",
    ) -> CompatibilityEngineResult:
        """Score déterministe pour une paire de réponses."""
        texts = [
            cls._normalize(a.get("text", ""))
            for a in answers_context
            if a.get("text") and str(a.get("text", "")).strip()
        ]

        if len(texts) < 2:
            return CompatibilityEngineResult(
                percent=cls.BASELINE,
                insight_local="En attente des deux réponses pour évaluer votre alignement.",
            )

        text_a, text_b = texts[0], texts[1]
        score = float(CATEGORY_BASELINE.get(category, cls.BASELINE))
        adjustments: list[str] = []
        matched_themes: list[str] = []

        exact = text_a == text_b
        overlap = cls._word_overlap_ratio(text_a, text_b)

        if exact:
            score += cls.EXACT_MATCH_BONUS
            adjustments.append("exact_match")
        else:
            score += overlap * cls.MAX_OVERLAP_BONUS
            adjustments.append(f"overlap:{overlap:.2f}")

        score += cls._apply_polarity(text_a, text_b, adjustments)

        for theme_id, keywords, bonus in THEME_RULES:
            if cls._contains_any(text_a, keywords) and cls._contains_any(text_b, keywords):
                theme_bonus = bonus
                if category and theme_id in CATEGORY_THEME_BOOST.get(category, []):
                    theme_bonus += cls.CATEGORY_THEME_EXTRA
                    adjustments.append(f"category_boost:{theme_id}")
                score += theme_bonus
                matched_themes.append(theme_id)
                adjustments.append(f"theme:{theme_id}+{theme_bonus}")

        for left_kw, right_kw, bonus in COMPLEMENTARY_PAIRS:
            if (cls._contains_any(text_a, left_kw) and cls._contains_any(text_b, right_kw)) or (
                cls._contains_any(text_a, right_kw) and cls._contains_any(text_b, left_kw)
            ):
                score += bonus
                adjustments.append(f"complementary+{bonus}")

        for left_kw, right_kw, penalty in TENSION_PAIRS:
            if (cls._contains_any(text_a, left_kw) and cls._contains_any(text_b, right_kw)) or (
                cls._contains_any(text_a, right_kw) and cls._contains_any(text_b, left_kw)
            ):
                score += penalty
                adjustments.append(f"tension{penalty}")

        q_norm = cls._normalize(question_text)
        if q_norm:
            for theme_id, keywords, bonus in THEME_RULES:
                if theme_id in matched_themes:
                    continue
                if cls._contains_any(q_norm, keywords):
                    if cls._contains_any(text_a, keywords) or cls._contains_any(text_b, keywords):
                        score += max(2, bonus // 3)
                        adjustments.append(f"question_theme:{theme_id}")

        percent = int(max(cls.MIN_PERCENT, min(cls.MAX_PERCENT, round(score))))
        insight_local = cls._build_local_insight(
            percent, matched_themes, exact, overlap, text_a, text_b
        )

        return CompatibilityEngineResult(
            percent=percent,
            insight_local=insight_local,
            matched_themes=matched_themes,
            exact_match=exact,
            word_overlap_ratio=overlap,
            adjustments=adjustments,
        )

    @classmethod
    def _apply_polarity(
        cls,
        text_a: str,
        text_b: str,
        adjustments: list[str],
    ) -> float:
        """Alignement positif / conflit de polarité entre les deux réponses."""
        delta = 0.0
        pos_a = cls._contains_any(text_a, POSITIVE_WORDS)
        pos_b = cls._contains_any(text_b, POSITIVE_WORDS)
        neg_a = cls._contains_any(text_a, NEGATIVE_WORDS)
        neg_b = cls._contains_any(text_b, NEGATIVE_WORDS)

        if pos_a and pos_b:
            delta += POSITIVE_ALIGNMENT_BONUS
            adjustments.append("positive_alignment")
        if (pos_a and neg_b) or (neg_a and pos_b):
            delta += POLARITY_CONFLICT_MALUS
            adjustments.append("polarity_conflict")
        if neg_a and neg_b and not (pos_a or pos_b):
            delta += SHARED_NEGATIVE_BONUS
            adjustments.append("shared_negative_understanding")
        return delta

    @staticmethod
    def _normalize(text: str) -> str:
        if not text:
            return ""
        lowered = text.lower().strip()
        nfkd = unicodedata.normalize("NFKD", lowered)
        asciiish = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", asciiish)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9']{3,}", text) if len(w) >= 3}

    @classmethod
    def _word_overlap_ratio(cls, a: str, b: str) -> float:
        ta, tb = cls._tokenize(a), cls._tokenize(b)
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union else 0.0

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(kw in text for kw in keywords)

    @classmethod
    def _build_local_insight(
        cls,
        percent: int,
        themes: list[str],
        exact: bool,
        overlap: float,
        text_a: str,
        text_b: str,
    ) -> str:
        if exact:
            return "Vous êtes parfaitement alignés sur cette question."

        if themes:
            label = THEME_LABELS.get(themes[0], themes[0])
            if percent >= 75:
                return f"Excellente compatibilité sur {label}."
            if percent >= 55:
                return f"Bonne convergence autour de {label}."
            return f"Des points communs sur {label}, avec des nuances à explorer."

        if overlap >= 0.35:
            return "Vos réponses se rejoignent sur plusieurs mots-clés importants."

        if percent >= 70:
            return FALLBACK_INSIGHTS[0] + " ❤️"
        if percent >= 55:
            return FALLBACK_INSIGHTS[min(1, len(FALLBACK_INSIGHTS) - 1)] + " ❤️"
        return (
            "Des différences à explorer avec curiosité — "
            "comme deux partenaires qui s'entraînent à s'aimer. ❤️"
        )

"""
Progression couple — niveau et score de compatibilité global.
"""
from __future__ import annotations

from django.conf import settings
from django.db import transaction

from apps.couples.models import Couple
from apps.game.models import QuestionRound


class CoupleProgressService:
    """Met à jour niveau et compatibilité globale après chaque tour."""

    @staticmethod
    def questions_per_level() -> int:
        return getattr(settings, "QUESTIONS_PER_LEVEL", 21)

    @staticmethod
    def count_completed_rounds(couple: Couple) -> int:
        return QuestionRound.objects.filter(couple=couple).count()

    @staticmethod
    def compute_level(total_rounds: int) -> int:
        """Niveau 1 au départ, +1 tous les 21 tours complétés."""
        return max(1, (total_rounds // CoupleProgressService.questions_per_level()) + 1)

    @staticmethod
    def level_progress(total_rounds: int) -> dict:
        """Progression dans le niveau actuel."""
        per_level = CoupleProgressService.questions_per_level()
        in_level = total_rounds % per_level
        remaining = per_level - in_level if in_level else 0
        return {
            "completed_in_level": in_level,
            "remaining_to_next": remaining,
            "per_level": per_level,
        }

    @staticmethod
    @transaction.atomic
    def apply_round_result(couple: Couple, round_percent: int) -> Couple:
        """Met à jour le score global et le niveau du couple."""
        couple = Couple.objects.select_for_update().get(pk=couple.pk)
        total = QuestionRound.objects.filter(couple=couple).count()
        if total <= 1:
            couple.compatibility_score = round_percent
        else:
            couple.compatibility_score = round(
                (couple.compatibility_score * (total - 1) + round_percent) / total
            )
        couple.compatibility_score = max(0, min(100, couple.compatibility_score))
        couple.level = CoupleProgressService.compute_level(total)
        couple.save(update_fields=["compatibility_score", "level"])
        return couple

    @staticmethod
    def get_stats(couple: Couple) -> dict:
        """Stats affichées dans la room et le dashboard."""
        total = CoupleProgressService.count_completed_rounds(couple)
        progress = CoupleProgressService.level_progress(total)
        return {
            "compatibility_score": couple.compatibility_score,
            "level": couple.level,
            "total_rounds": total,
            **progress,
        }

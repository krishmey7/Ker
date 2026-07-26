"""
Compatibilité couple — moteur déterministe (score) + IA optionnelle (analyse).
"""
from __future__ import annotations

from django.db import transaction

from apps.couples.models import Couple
from apps.game.models import Answer, GameSession, QuestionRound
from apps.game.services.compatibility_engine import CompatibilityEngine
from apps.game.services.couple_progress_service import CoupleProgressService


class CompatibilityService:
    """
    Enregistre les tours joués.

    Flux :
        1. CompatibilityEngine → percent (source de vérité)
        2. RelationshipAI → insight (enrichissement, optionnel)
        3. Fallback local si IA indisponible
    """

    @staticmethod
    def build_answers_context(session: GameSession) -> list[dict]:
        """Contexte des réponses pour le moteur et l'IA."""
        if not session.current_question_id:
            return []
        return [
            {
                "user_id": a.user_id,
                "label": a.user.label,
                "text": a.text,
            }
            for a in Answer.objects.filter(
                session=session,
                question_id=session.current_question_id,
            ).select_related("user")
        ]

    @staticmethod
    def compute_round_result(
        question_text: str,
        answers_ctx: list[dict],
        category: str = "",
    ) -> dict:
        """
        Calcule percent + insight sans persister.

        Returns:
            {"percent": int, "insight": str, "ai_enriched": bool}
        """
        engine_result = CompatibilityEngine.calculate(
            question_text, answers_ctx, category=category
        )
        from apps.ai.services.relationship_ai import RelationshipAI

        insight, ai_enriched = RelationshipAI().enrich(
            question_text,
            answers_ctx,
            percent=engine_result.percent,
            insight_local=engine_result.insight_local,
            matched_themes=engine_result.matched_themes,
        )
        return {
            "percent": engine_result.percent,
            "insight": insight[:500],
            "ai_enriched": ai_enriched,
        }

    @staticmethod
    @transaction.atomic
    def record_round(session: GameSession) -> QuestionRound:
        """
        Calcule et persiste la compatibilité pour la question en cours.
        Idempotent si le tour existe déjà.
        """
        if not session.current_question_id:
            raise ValueError("Aucune question active.")

        existing = QuestionRound.objects.filter(
            session=session,
            question_id=session.current_question_id,
        ).first()
        if existing:
            return existing

        answers_ctx = CompatibilityService.build_answers_context(session)
        question = session.current_question
        question_text = question.text if question else ""
        category = question.category if question else ""

        result = CompatibilityService.compute_round_result(
            question_text, answers_ctx, category=category
        )

        round_obj = QuestionRound.objects.create(
            couple=session.couple,
            session=session,
            question_id=session.current_question_id,
            compatibility_percent=result["percent"],
            compatibility_insight=result["insight"],
        )
        CoupleProgressService.apply_round_result(session.couple, result["percent"])
        return round_obj

    @staticmethod
    def get_history_for_couple(couple: Couple) -> list[dict]:
        """Historique des questions répondues à deux, pour la page historique."""
        rounds = (
            QuestionRound.objects.filter(couple=couple)
            .select_related("question", "session")
            .order_by("-played_at")
        )
        history = []
        for rnd in rounds:
            answers = (
                Answer.objects.filter(session=rnd.session, question=rnd.question)
                .select_related("user")
                .order_by("user_id")
            )
            history.append(
                {
                    "round": rnd,
                    "question": rnd.question,
                    "answers": list(answers),
                    "compatibility_percent": rnd.compatibility_percent,
                    "compatibility_insight": rnd.compatibility_insight,
                    "played_at": rnd.played_at,
                }
            )
        return history

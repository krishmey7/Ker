"""Provider statique — fallback sans appel réseau."""
import random

from apps.ai.services.base import AIProvider
from apps.ai.services.prompts import normalize_category
from apps.ai.services.static_data import STATIC_PHRASES, STATIC_QUESTIONS


class StaticProvider(AIProvider):
    """Réponses prédéfinies pour dev, tests et secours."""

    def generate_text(self, prompt: str) -> str:
        """Retourne une phrase générique (pas d'interprétation du prompt)."""
        return random.choice(STATIC_PHRASES)

    def generate_questions(
        self,
        category: str,
        count: int,
        spicy_level: int = 0,
        exclude_texts: list[str] | None = None,
    ) -> list[dict]:
        cat = normalize_category(category)
        pool = [q for q in STATIC_QUESTIONS if q["category"] == cat or not cat]
        if not pool:
            pool = STATIC_QUESTIONS
        if exclude_texts:
            excluded = {t.strip().lower() for t in exclude_texts}
            pool = [q for q in pool if q["text"].strip().lower() not in excluded]
        if not pool:
            pool = STATIC_QUESTIONS
        selected = random.sample(pool, min(count, len(pool)))
        return [
            {
                "text": item["text"],
                "category": item.get("category", cat),
                "spicy_level": item.get("spicy_level", spicy_level),
            }
            for item in selected
        ]

    def generate_emotional_phrase(self, context: str = "") -> str:
        return random.choice(STATIC_PHRASES)

    def compatibility_summary(self, answers_context: list[dict]) -> str:
        texts = [a.get("text", "").lower().strip() for a in answers_context if a.get("text")]
        if len(texts) >= 2 and texts[0] == texts[1]:
            return "Vous êtes sur la même longueur d'onde sur celle-ci."
        return "Votre relation semble basée sur l'humour et la spontanéité."

    def calculate_compatibility_score(
        self, question_text: str, answers_context: list[dict]
    ) -> dict:
        """Délègue au moteur déterministe + fallback texte local (sans API)."""
        from apps.game.services.compatibility_service import CompatibilityService

        if not answers_context:
            return {"percent": 50, "insight": "En attente des deux réponses."}
        result = CompatibilityService.compute_round_result(question_text, answers_context)
        return {"percent": result["percent"], "insight": result["insight"][:300]}

    def suggest_couple_activity(
        self,
        compatibility_score: int,
        level: int,
        recent_topics: list[str],
    ) -> dict:
        """Activité statique selon le niveau de compatibilité."""
        if compatibility_score >= 80:
            title = "Soirée souvenirs"
            description = (
                "Préparez chacun trois photos qui racontent un moment fort de votre relation. "
                "Partagez-les à tour de rôle en expliquant pourquoi ce moment compte."
            )
        elif compatibility_score >= 60:
            title = "Défi cuisine à deux"
            description = (
                "Choisissez une recette simple et cuisinez-la ensemble sans téléphone. "
                "Chacun gère une partie du plat et goûte avant de servir."
            )
        else:
            title = "Pause sincérité"
            description = (
                "Installez-vous face à face pendant 10 minutes. "
                "Chacun partage une chose qu'il apprécie chez l'autre cette semaine."
            )
        return {
            "title": title,
            "description": description,
            "duration_minutes": 30 + level * 5,
            "tips": "Coupez les notifications pour rester présents l'un pour l'autre.",
        }

"""
Cadre pédagogique — « Ce que j'aurais aimé savoir avant de me marier » (Gary Chapman).

Inspire la banque de 1000 questions, les prompts IA et les analyses locales.
"""
from __future__ import annotations

from apps.game.models import QuestionCategory

BOOK_TITLE = "Ce que j'aurais aimé savoir avant de me marier"
BOOK_AUTHOR = "Gary Chapman"

CHAPMAN_COACH_SYSTEM = f"""Tu t'inspires de « {BOOK_TITLE} » ({BOOK_AUTHOR}), conseiller conjugal.
Contexte culturel : République Démocratique du Congo (RDC) — valeurs familiales africaines, solidarité communautaire, respect des aînés, importance de la foi et de la tradition.
Objectif : rapprocher les partenaires par la conversation honnête, pas par le jugement.

Principes adaptés au contexte RDC :
- L'amour romantique initial ne suffit pas ; construire une équipe intime demande apprentissage.
- Chacun a un « langage de l'amour » (paroles, services, cadeaux, temps de qualité, toucher).
- On est influencé par sa famille ; on peut choisir de ne pas répéter les schémas nuisibles.
- Les désaccords se règlent sans humiliation : écoute active, résumé, compromis.
- Les excuses et le pardon sont des compétences (pas seulement des sentiments).
- Foyer, argent et intimité se préparent à deux, avec respect et consentement mutuel.
- Épouser quelqu'un, c'est aussi accueillir son histoire familiale et sa communauté.
- Compatibilité spirituelle = ce que chacun croit et comment il vit sa foi au quotidien (chrétienne, musulmane, traditionnelle).
- Les différences de personnalité (matin/soir, rangé/bordélique…) s'apprivoisent, ne disparaissent pas.
- La famille élargie (oncles, tantes, cousins) joue un rôle important dans la vie du couple.
- La solidarité et l'entraide communautaire sont des valeurs centrales en RDC."""

CHAPMAN_QUESTION_RULES = """
- Question courte (max 200 caractères), en français, pour un couple déjà ensemble en RDC.
- Ton bienveillant, concret, orienté « nous » et compréhension mutuelle (pas de diagnostic).
- Contextualise avec la réalité congolaise : famille élargie, solidarité, foi, traditions, défis quotidiens.
- Pas de honte, pas de violence, pas d'explicite sexuel sauf spicy_level ≥ 2 (tact et consentement).
- Invite à écouter l'autre et à préparer la vie à deux (communication, valeurs, habitudes).
- Évite les doublons avec les questions déjà posées."""

CHAPMAN_ANALYSIS_RULES = """
- Analyse comme un coach Chapman adapté à la RDC : valorise l'écoute, le compromis, les langages de l'amour.
- Si les réponses divergent, encourage la curiosité bienveillante, pas la victoire.
- Mentionne un prochain pas concret adapté au contexte (parler, s'excuser, temps de qualité, budget, famille élargie, communauté…).
- Ne moralise pas, ne cite pas le livre mot pour mot."""

CHAPTERS: list[dict] = [
    {"id": 1, "title": "Être amoureux ne suffit pas pour un mariage heureux", "categories": (QuestionCategory.DEEP, QuestionCategory.ROMANTIC)},
    {"id": 2, "title": "Deux étapes dans l'amour et langages de l'amour", "categories": (QuestionCategory.ROMANTIC, QuestionCategory.KNOW_PARTNER)},
    {"id": 3, "title": "Influence des parents (telle mère, telle fille…)", "categories": (QuestionCategory.KNOW_PARTNER, QuestionCategory.DEEP)},
    {"id": 4, "title": "Régler les désaccords sans se disputer", "categories": (QuestionCategory.HABITS, QuestionCategory.DEEP)},
    {"id": 5, "title": "S'excuser est une force", "categories": (QuestionCategory.DEEP, QuestionCategory.HABITS)},
    {"id": 6, "title": "Le pardon n'est pas seulement un sentiment", "categories": (QuestionCategory.DEEP,)},
    {"id": 7, "title": "Le foyer et les tâches du quotidien", "categories": (QuestionCategory.HABITS,)},
    {"id": 8, "title": "Gérer l'argent à deux", "categories": (QuestionCategory.FUTURE, QuestionCategory.HABITS)},
    {"id": 9, "title": "Épanouissement mutuel et intimité", "categories": (QuestionCategory.SPICY, QuestionCategory.ROMANTIC)},
    {"id": 10, "title": "Épouser aussi une famille", "categories": (QuestionCategory.KNOW_PARTNER, QuestionCategory.FUTURE)},
    {"id": 11, "title": "Spiritualité au-delà de « aller à l'église »", "categories": (QuestionCategory.DEEP,)},
    {"id": 12, "title": "Personnalité et habitudes opposées", "categories": (QuestionCategory.KNOW_PARTNER, QuestionCategory.FUNNY)},
]

CHAPMAN_FALLBACK_INSIGHTS: list[str] = [
    "Vous avancez comme une équipe : écoutez-vous encore un tour avant de conclure.",
    "Vos réponses montrent des langages de l'amour différents — une richesse à explorer.",
    "Belle convergence : le pardon et le compromis sont à portée de main.",
    "Vous partagez des valeurs de fond — cultivez-les par de petits gestes concrets.",
    "Des nuances à accueillir avec curiosité, comme Chapman le recommande avant le mariage.",
    "Votre complémentarité peut devenir une force si vous la nommez à voix haute.",
    "Votre famille élargie peut être une ressource si vous l'intégrez sagement dans votre couple.",
    "La solidarité communautaire congolaise peut renforcer votre lien si vous l'ouvrez aux autres.",
]

CHAPMAN_FALLBACK_TIPS: list[str] = [
    "Reformulez la réponse de l'autre avant d'ajouter la vôtre (écoute active).",
    "Offrez aujourd'hui un geste dans le langage de l'amour de votre partenaire.",
    "Parlez d'une tâche maison à répartir clairement cette semaine.",
    "Fixez un seuil d'achat au-delà duquel vous consultez toujours l'autre.",
    "Passez 20 minutes de qualité sans écran, face à face.",
    "Dites une excuse complète : regret, responsabilité et projet de changement.",
    "Nommez une qualité de vos beaux-parents que vous voulez honorer.",
    "Invitez un membre de la famille élargie à partager un moment avec vous.",
    "Participez ensemble à une activité communautaire ou religieuse de votre quartier.",
]

from apps.game.data.chapman_bank_builder import (  # noqa: E402
    BANK_TARGETS,
    generate_chapman_bank_questions,
)

__all__ = [
    "BOOK_TITLE",
    "BOOK_AUTHOR",
    "CHAPMAN_COACH_SYSTEM",
    "CHAPMAN_QUESTION_RULES",
    "CHAPMAN_ANALYSIS_RULES",
    "CHAPTERS",
    "CHAPMAN_FALLBACK_INSIGHTS",
    "CHAPMAN_FALLBACK_TIPS",
    "BANK_TARGETS",
    "generate_chapman_bank_questions",
]

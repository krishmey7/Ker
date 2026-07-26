"""Prompts centralisés — faciles à faire évoluer."""
from apps.game.data.chapman_framework import (
    BOOK_AUTHOR,
    BOOK_TITLE,
    CHAPMAN_ANALYSIS_RULES,
    CHAPMAN_COACH_SYSTEM,
    CHAPMAN_QUESTION_RULES,
)

# Labels pour les choix de durée de relation
DURATION_LABELS = {
    "less_than_1_year": "Moins d'un an",
    "1_to_3_years": "1 à 3 ans",
    "more_than_3_years": "Plus de 3 ans",
    "engaged": "Fiancés",
}

# Labels pour les continents
CONTINENT_LABELS = {
    "africa": "Afrique",
    "europe": "Europe",
    "north_america": "Amérique du Nord",
    "south_america": "Amérique du Sud",
    "asia": "Asie",
    "oceania": "Océanie",
}

CATEGORY_LABELS = {
    "romantic": "langages de l'amour et tendresse (Chapman)",
    "funny": "personnalités complémentaires, léger et bienveillant",
    "spicy": "intimité respectueuse et consentie (Chapman, ch.9)",
    "deep": "fondations, pardon, spiritualité, valeurs",
    "know_partner": "famille d'origine, belle-famille, connaissance mutuelle",
    "future": "projets, argent, foyer à construire",
    "habits": "communication, conflits, tâches du quotidien",
}

CATEGORY_ALIASES = {
    "romantique": "romantic",
    "drôle": "funny",
    "drole": "funny",
    "profond": "deep",
    "spicy": "spicy",
}


def normalize_category(category: str) -> str:
    """Normalise une catégorie (fr/en) vers la clé interne."""
    key = (category or "").strip().lower()
    return CATEGORY_ALIASES.get(key, key or "romantic")


def question_prompt(
    category: str,
    count: int = 1,
    spicy_level: int = 0,
    exclude_texts: list[str] | None = None,
) -> str:
    """Prompt pour générer des questions de couple (cadre Gary Chapman)."""
    label = CATEGORY_LABELS.get(category, category)
    exclude_block = ""
    if exclude_texts:
        lines = "\n".join(f'- "{t[:180]}"' for t in exclude_texts[:30])
        exclude_block = f"""
Questions DÉJÀ posées — n'en propose AUCUNE de similaire ni identique :
{lines}
"""
    return f"""{CHAPMAN_COACH_SYSTEM}

Référence : « {BOOK_TITLE} » — {BOOK_AUTHOR}.

Génère exactement {count} question(s) en français, ton {label}.
Niveau spicy (0-3) : {spicy_level}.
{exclude_block}
{CHAPMAN_QUESTION_RULES}

Format JSON strict uniquement, sans markdown :
[{{"text": "...", "category": "{category}", "spicy_level": {spicy_level}}}]
"""


def single_question_prompt(
    category: str,
    spicy_level: int = 0,
    exclude_texts: list[str] | None = None,
) -> str:
    """Prompt pour une seule question."""
    return question_prompt(category, count=1, spicy_level=spicy_level, exclude_texts=exclude_texts)


def emotional_phrase_prompt(context: str = "") -> str:
    """Prompt pour une phrase émotionnelle courte."""
    extra = f" Contexte : {context}" if context else ""
    return f"""{CHAPMAN_COACH_SYSTEM}

Écris une seule phrase courte en français (max 120 caractères),
encourageante pour un couple qui apprend à mieux se comprendre.{extra}
Réponds uniquement avec la phrase, sans guillemets ni explication."""


def compatibility_prompt(answers_context: list[dict]) -> str:
    """Prompt pour un résumé de compatibilité."""
    lines = "\n".join(
        f"- {a.get('label', 'Partenaire')} : {a.get('text', '')}" for a in answers_context[:6]
    )
    return f"""{CHAPMAN_COACH_SYSTEM}

Analyse ces réponses de couple et écris UN résumé en français (max 150 caractères),
chaleureux, orienté rapprochement et prochain pas concret :
{lines}
{CHAPMAN_ANALYSIS_RULES}
Réponds uniquement avec le résumé."""


def compatibility_enrichment_prompt(
    question_text: str,
    answers_context: list[dict],
    percent: int,
    matched_themes: list[str],
    local_summary: str,
) -> str:
    """
    Prompt d'enrichissement — le score est DÉJÀ FIXÉ, l'IA ne doit pas le recalculer.
    """
    lines = "\n".join(
        f"- {a.get('label', 'Partenaire')} : {a.get('text', '')}" for a in answers_context[:6]
    )
    themes = ", ".join(matched_themes) if matched_themes else "non détectés"
    return f"""{CHAPMAN_COACH_SYSTEM}

Score de compatibilité DÉJÀ CALCULÉ (ne le modifie pas, ne le mentionne pas en chiffre) : {percent}%
Thèmes détectés par le moteur : {themes}
Résumé technique local : {local_summary}

Question : « {question_text} »

Réponses :
{lines}

Écris UNIQUEMENT une analyse courte en français (2-3 phrases max, 280 caractères max) :
{CHAPMAN_ANALYSIS_RULES}
Réponds uniquement avec le texte d'analyse."""


def compatibility_score_prompt(question_text: str, answers_context: list[dict]) -> str:
    """Prompt pour un score de compatibilité en pourcentage (JSON strict)."""
    lines = "\n".join(
        f"- {a.get('label', 'Partenaire')} : {a.get('text', '')}" for a in answers_context[:6]
    )
    return f"""{CHAPMAN_COACH_SYSTEM}

Question posée : « {question_text} »

Réponses :
{lines}

Évalue la convergence émotionnelle et la capacité à avancer ensemble (écoute, compromis, respect).
Réponds UNIQUEMENT en JSON strict, sans markdown :
{{"percent": <entier 0-100>, "insight": "<phrase courte en français, max 140 caractères>"}}
"""


def couple_activity_prompt(
    compatibility_score: int,
    level: int,
    recent_topics: list[str],
) -> str:
    """Prompt pour une activité de couple personnalisée."""
    topics = ", ".join(recent_topics[:5]) if recent_topics else "communication, complicité, foyer"
    return f"""{CHAPMAN_COACH_SYSTEM}

Compatibilité globale du couple : {compatibility_score}%.
Niveau de progression : {level}.
Thèmes récents : {topics}.

Propose UNE activité de couple concrète (temps de qualité, dialogue, service, pardon, budget…),
réalisable chez soi ou en sortie courte, dans l'esprit de la préparation au mariage heureux.
Réponds UNIQUEMENT en JSON strict, sans markdown :
{{"title": "<titre court>", "description": "<description engageante, 2-3 phrases>", "duration_minutes": <entier>, "tips": "<conseil pratique, 1 phrase>"}}
"""


def get_adaptive_system_prompt(couple_context: dict) -> str:
    """
    Génère un prompt système adapté au profil du couple.
    
    Args:
        couple_context: dict avec clés 'relationship_duration', 'is_long_distance', 'residence_continent'
    
    Returns:
        str: Prompt système personnalisé
    """
    duration_key = couple_context.get("relationship_duration", "less_than_1_year")
    duration_label = DURATION_LABELS.get(duration_key, "Moins d'un an")
    
    is_long_distance = couple_context.get("is_long_distance", False)
    distance_label = "Oui" if is_long_distance else "Non"
    
    continent_key = couple_context.get("residence_continent", "africa")
    continent_label = CONTINENT_LABELS.get(continent_key, "Afrique")
    
    return f"""Tu es l'IA expert relationnel de l'application K'er. Ton objectif est de poser des questions qui renforcent la complicité du couple et les aident à cheminer vers un engagement durable (le mariage).

CONTEXTE DU COUPLE :
- Durée de relation : {duration_label}
- Relation à distance : {distance_label}
- Continent : {continent_label}

DIRECTIVES D'ADAPTATION :
1. DURÉE :
   - 'Moins d'un an' : Questions axées sur la découverte ludique, les coups de cœur, les anecdotes et les premières impressions.
   - '1-3 ans' : Questions sur la compatibilité au quotidien, la résolution de petits désaccords, les valeurs partagées.
   - 'Plus de 3 ans' & 'Fiancés' : Questions plus profondes sur les projets de vie, la vision du mariage, la famille, la gestion de l'avenir commun.

2. RELATION À DISTANCE :
   - Si OUI : Intégrer des questions sur les retrouvailles, la gestion du manque, la communication digitale, les rituels à distance et les projets de rapprochement.

3. CONTINENT & CULTURE :
   - Adapter les expressions, le ton et les références culturelles subtilement selon le continent ({continent_label}) sans tomber dans les clichés.

4. OBJECTIF ULTIME :
   - Garder une touche chaleureuse, ludique et romantique. Favoriser l'échange constructif.
   - NE JAMAIS mentionner "mariés" - le couple est en chemin vers le mariage, pas encore marié.
"""

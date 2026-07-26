"""Utilitaires de parsing des réponses LLM (JSON, markdown)."""
from __future__ import annotations

import json
import re

from apps.ai.services.prompts import normalize_category


def parse_json_object(raw: str) -> dict:
    """Extrait un objet JSON depuis une réponse modèle."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("JSON attendu : objet.")
    return data


def parse_questions_json(raw: str, category: str, spicy_level: int) -> list[dict]:
    """Extrait une liste de questions depuis la réponse modèle."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        return []
    results = []
    for item in data:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        results.append(
            {
                "text": str(item["text"]).strip()[:500],
                "category": normalize_category(item.get("category", category)),
                "spicy_level": int(item.get("spicy_level", spicy_level)),
            }
        )
    return results

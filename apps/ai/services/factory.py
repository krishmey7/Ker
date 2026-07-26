"""Factory — sélection du provider IA configuré."""
from django.conf import settings

from apps.ai.services.base import AIProvider
from apps.ai.services.gemini_provider import GeminiProvider
from apps.ai.services.groq_provider import GroqProvider
from apps.ai.services.static_provider import StaticProvider

_provider_cache: AIProvider | None = None


def is_live_ai_configured() -> bool:
    """True si un provider cloud (Groq/Gemini) est configuré avec une clé API."""
    name = getattr(settings, "AI_PROVIDER", "static").lower()
    if name == "groq":
        return bool(getattr(settings, "GROQ_API_KEY", ""))
    if name == "gemini":
        return bool(getattr(settings, "GEMINI_API_KEY", ""))
    return False


def is_live_provider(provider: AIProvider) -> bool:
    """True si le provider courant appelle une API externe."""
    return provider.name in ("GroqProvider", "GeminiProvider")


def get_provider(force_refresh: bool = False) -> AIProvider:
    """
    Retourne le provider actif (singleton).
    Priorité : AI_PROVIDER=groq + GROQ_API_KEY, sinon gemini, sinon static.
    """
    global _provider_cache
    if _provider_cache is not None and not force_refresh:
        return _provider_cache

    provider_name = getattr(settings, "AI_PROVIDER", "static").lower()

    if provider_name == "groq":
        api_key = getattr(settings, "GROQ_API_KEY", "")
        if api_key:
            _provider_cache = GroqProvider(
                api_key=api_key,
                model_name=getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
            )
            return _provider_cache

    if provider_name == "gemini":
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if api_key:
            _provider_cache = GeminiProvider(
                api_key=api_key,
                model_name=getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash"),
            )
            return _provider_cache

    _provider_cache = StaticProvider()
    return _provider_cache

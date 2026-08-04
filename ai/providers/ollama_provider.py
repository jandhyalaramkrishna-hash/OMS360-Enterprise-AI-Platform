"""
AI Service Layer - Providers - Ollama (prepared, not called)
OMS-360 Enterprise Food Delivery Platform

Sprint 2 scope: structurally real, correctly reports configuration state.
Unlike the hosted providers, Ollama needs no API key - it is considered
"configured" only when OLLAMA_BASE_URL is explicitly set (deliberately
not defaulted to localhost, to keep this fail-closed like every other
provider rather than silently assuming a local server is present).
complete() deliberately does not call Ollama. No SDK dependency has been
added to requirements.txt ("no unnecessary dependencies"). Wiring a real
call is a future, explicitly-scoped sprint.
"""

import os

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderNotConfiguredError
from ai.providers.base import BaseProvider

logger = get_logger("ai.providers.ollama")


class OllamaProvider(BaseProvider):
    name = "ollama"
    required_env_vars = ("OLLAMA_BASE_URL",)

    def is_configured(self) -> bool:
        return bool(os.environ.get("OLLAMA_BASE_URL", "").strip())

    async def complete(self, prompt: str, **kwargs) -> dict:
        logger.warning("OllamaProvider.complete() called - not implemented in Sprint 2")
        raise AIProviderNotConfiguredError(
            "OllamaProvider is prepared but not yet wired to make API calls (Sprint 2 scope: preparation only)."
        )

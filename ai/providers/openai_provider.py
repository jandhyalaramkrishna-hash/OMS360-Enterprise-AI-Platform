"""
AI Service Layer - Providers - OpenAI (prepared, not called)
OMS-360 Enterprise Food Delivery Platform

Sprint 2 scope: this provider is structurally real - it correctly
reports whether it's configured - but complete() deliberately does not
call the OpenAI API. No `openai` SDK dependency has been added to
requirements.txt, since nothing here calls it yet ("no unnecessary
dependencies"). Wiring a real call is a future, explicitly-scoped sprint.
"""

import os

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderNotConfiguredError
from ai.providers.base import BaseProvider

logger = get_logger("ai.providers.openai")


class OpenAIProvider(BaseProvider):
    name = "openai"
    required_env_vars = ("OPENAI_API_KEY",)

    def is_configured(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())

    async def complete(self, prompt: str, **kwargs) -> dict:
        logger.warning("OpenAIProvider.complete() called - not implemented in Sprint 2")
        raise AIProviderNotConfiguredError(
            "OpenAIProvider is prepared but not yet wired to make API calls (Sprint 2 scope: preparation only)."
        )

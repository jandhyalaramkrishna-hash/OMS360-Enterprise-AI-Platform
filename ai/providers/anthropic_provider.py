"""
AI Service Layer - Providers - Anthropic (prepared, not called)
OMS-360 Enterprise Food Delivery Platform

Sprint 2 scope: structurally real, correctly reports configuration state;
complete() deliberately does not call the Anthropic API. No `anthropic`
SDK dependency has been added to requirements.txt ("no unnecessary
dependencies"). Wiring a real call is a future, explicitly-scoped sprint.
"""

import os

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderNotConfiguredError
from ai.providers.base import BaseProvider

logger = get_logger("ai.providers.anthropic")


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    required_env_vars = ("ANTHROPIC_API_KEY",)

    def is_configured(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    async def complete(self, prompt: str, **kwargs) -> dict:
        logger.warning("AnthropicProvider.complete() called - not implemented in Sprint 2")
        raise AIProviderNotConfiguredError(
            "AnthropicProvider is prepared but not yet wired to make API calls (Sprint 2 scope: preparation only)."
        )

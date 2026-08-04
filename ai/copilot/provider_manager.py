"""
AI Copilot - AI Provider Manager
OMS-360 Enterprise Food Delivery Platform

Reuses the existing Sprint 4 ProviderRegistry (ai/providers/registry.py)
and the existing provider adapters (ai/providers/*.py) unmodified - this
module adds exactly one new thing: an AUTO-selection policy across
*real* (non-mock) providers, plus an explicit, honest "no provider
configured" outcome instead of raising.

Why a new component rather than reusing AIService.get_selected_provider():
that method requires exactly one provider name to already be chosen via
AI_PROVIDER_NAME/AI_PROVIDER and raises AIProviderNotConfiguredError if
none is set - by design, for the Sprint 1-9 AI Runtime, which always
assumed a human explicitly picks one provider. AI Copilot needs a
different, additive policy on top of the same registry: try every real
provider in a fixed preference order and use whichever one is actually
configured, so the application "just works" for a student with no API
key (falls through to the deterministic engine) and for a company that
sets exactly one provider's credentials (that one is picked
automatically, no AI_PROVIDER_NAME env var required). This module does
not change ProviderRegistry, AIService, or any existing provider
adapter - it is a thin policy layer reading the same registry.

The "mock" provider (ai/providers/mock_provider.py) is deliberately
EXCLUDED from the AUTO chain: MockAIProvider only echoes the input text
back with a "[mock] " prefix - it cannot perform real reasoning, so
treating it as a "configured LLM" would be misleading. If no real
provider is configured, AIProviderManager reports that honestly
(active_provider is None) and callers fall back to the deterministic
business engine / plain templates - never to the mock echo.
"""

from dataclasses import dataclass
from typing import Optional

from app.core.logging_config import get_logger

from ai.providers.base import BaseProvider
from ai.providers.registry import ProviderRegistry

logger = get_logger("ai.copilot.provider_manager")

# Fixed preference order for AUTO mode. Deliberately excludes "mock" (see
# module docstring). Order matches the sequence given in the approved
# architecture: OpenAI -> Anthropic -> Ollama -> Azure OpenAI -> none.
_AUTO_PREFERENCE_ORDER = ("openai", "anthropic", "ollama", "azure_openai")


@dataclass(frozen=True)
class ProviderSelection:
    """The outcome of AIProviderManager.get_active_provider()."""

    provider: Optional[BaseProvider]
    source: str  # "explicit" | "auto" | "none_configured"
    reasoning_available: bool

    @property
    def provider_name(self) -> Optional[str]:
        return self.provider.name if self.provider else None


class AIProviderManager:
    """AUTO-selects a real, configured LLM provider from the existing
    ProviderRegistry, or reports that none is configured. Construct via
    ai.dependencies.get_provider_manager() (shares the SAME
    ProviderRegistry singleton every other AI Runtime component already
    uses), not directly."""

    def __init__(self, provider_registry: ProviderRegistry, explicit_provider_name: str = ""):
        self._registry = provider_registry
        # An explicit override (e.g. AI_COPILOT_PROVIDER env var, read by
        # ai.dependencies at construction time) always wins over AUTO -
        # "a company can plug in their own API key" also covers "and pin
        # a specific one deliberately", not just whichever is found first.
        self._explicit_provider_name = (explicit_provider_name or "").strip()

    def get_active_provider(self) -> ProviderSelection:
        if self._explicit_provider_name and self._explicit_provider_name != "mock":
            try:
                provider = self._registry.get_provider(self._explicit_provider_name)
            except Exception:
                provider = None
            if provider is not None and provider.is_configured():
                logger.info(
                    "AI Copilot provider selected (explicit)",
                    extra={"ctx_provider_name": provider.name},
                )
                return ProviderSelection(provider=provider, source="explicit", reasoning_available=True)
            logger.warning(
                "AI Copilot explicit provider is not configured - falling back to AUTO",
                extra={"ctx_explicit_provider_name": self._explicit_provider_name},
            )

        for name in _AUTO_PREFERENCE_ORDER:
            try:
                provider = self._registry.get_provider(name)
            except Exception:
                continue
            if provider.is_configured():
                logger.info("AI Copilot provider selected (auto)", extra={"ctx_provider_name": provider.name})
                return ProviderSelection(provider=provider, source="auto", reasoning_available=True)

        logger.info("AI Copilot: no real LLM provider configured - deterministic-only mode")
        return ProviderSelection(provider=None, source="none_configured", reasoning_available=False)

    def status(self) -> dict:
        """A small, UI-friendly snapshot: which provider (if any) is
        currently active, and which real providers were checked."""
        selection = self.get_active_provider()
        return {
            "active_provider": selection.provider_name,
            "source": selection.source,
            "reasoning_available": selection.reasoning_available,
            "checked_providers": list(_AUTO_PREFERENCE_ORDER),
        }

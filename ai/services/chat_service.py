"""
AI Service Layer - Services - AI Chat Service (Sprint 4)
OMS-360 Enterprise Food Delivery Platform

The first component in this project that actually calls a provider's
complete() and gets back a real result - in Sprint 4 that is always
MockAIProvider, since this sprint explicitly excludes implementing any
real provider (OpenAI/Claude/Gemini/Azure OpenAI). Composes already-built
collaborators rather than reaching into globals directly (Dependency
Inversion): AIService (master AI_ENABLED gate + configuration-based
provider selection via RuntimeConfiguration.provider_name),
ProviderRegistry (explicit provider-name override), ProviderHealthChecker
(live liveness probing), and AIMetrics (request/response/error/latency
counters, already built in Sprint 2).
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from app.core.logging_config import get_logger

from ai.core.exceptions import (
    AIChatInvalidRequestError,
    AIFeatureDisabledError,
    AIProviderNotConfiguredError,
    AIServiceError,
)
from ai.metrics import AIMetrics
from ai.providers.health import ProviderHealthChecker, ProviderHealthResult
from ai.providers.registry import ProviderRegistry
from ai.services.ai_service import AIService

logger = get_logger("ai.services.chat")


@dataclass(frozen=True)
class ChatResult:
    """The outcome of a single AIChatService.send_message() call."""

    provider: str
    content: str
    model: Optional[str]
    usage: dict = field(default_factory=dict)
    is_mock: bool = False


class AIChatService:
    """Constructed via ServiceFactory.build_chat_service() or the shared
    ai.dependencies.get_chat_service() singleton - not directly."""

    def __init__(
        self,
        ai_service: AIService,
        provider_registry: ProviderRegistry,
        health_checker: ProviderHealthChecker,
        metrics: AIMetrics,
    ):
        self._ai_service = ai_service
        self._provider_registry = provider_registry
        self._health_checker = health_checker
        self._metrics = metrics
        logger.info("AIChatService initialized")

    def _resolve_provider(self, provider_name: Optional[str]):
        """Configuration-based provider selection: an explicit
        provider_name argument overrides the configured default; otherwise
        the provider selected via RuntimeConfiguration.provider_name
        (AI_PROVIDER_NAME/AI_PROVIDER) is used, exactly as
        AIService.get_selected_provider() already resolves it."""
        if provider_name:
            return self._provider_registry.get_provider(provider_name)
        return self._ai_service.get_selected_provider()

    async def send_message(self, message: str, provider_name: Optional[str] = None) -> ChatResult:
        """Sends a single message to the selected (or explicitly named)
        provider and returns its response. Raises AIChatInvalidRequestError
        for a blank message, AIFeatureDisabledError if AI_ENABLED is false,
        AIProviderNotConfiguredError if no provider is selected/configured,
        or AIProviderNotFoundError if an explicit provider_name isn't
        registered."""
        if not isinstance(message, str) or not message.strip():
            raise AIChatInvalidRequestError()

        status = self._ai_service.status()
        if not status.ai_enabled:
            raise AIFeatureDisabledError()

        provider = self._resolve_provider(provider_name)
        if not provider.is_configured():
            raise AIProviderNotConfiguredError(f"Provider '{provider.name}' is not configured.")

        self._metrics.record_request()
        start = time.monotonic()
        try:
            raw = await provider.complete(message)
        except AIServiceError:
            self._metrics.record_error()
            raise
        latency_ms = (time.monotonic() - start) * 1000
        self._metrics.record_provider_latency(provider.name, latency_ms)

        usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
        self._metrics.record_response(token_usage=usage.get("total_tokens", 0))

        logger.info(
            "AIChatService.send_message completed",
            extra={"ctx_provider_name": provider.name, "ctx_latency_ms": round(latency_ms, 2)},
        )

        return ChatResult(
            provider=provider.name,
            content=raw.get("content", "") if isinstance(raw, dict) else str(raw),
            model=raw.get("model") if isinstance(raw, dict) else None,
            usage=usage,
            is_mock=(provider.name == "mock"),
        )

    async def health_check(self, provider_name: Optional[str] = None) -> ProviderHealthResult:
        """Live health probe of the selected (or explicitly named)
        provider. See ProviderHealthChecker for what "live" means here."""
        provider = self._resolve_provider(provider_name)
        return await self._health_checker.check(provider)

    async def health_check_all(self) -> list:
        """Live health probe of every provider registered in this
        service's ProviderRegistry, not just the selected one."""
        providers = [self._provider_registry.get_provider(n) for n in self._provider_registry.list_providers()]
        return await self._health_checker.check_all(providers)

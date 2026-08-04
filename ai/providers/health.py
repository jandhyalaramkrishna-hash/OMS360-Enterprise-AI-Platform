"""
AI Service Layer - Providers - Provider health checker (Sprint 4)
OMS-360 Enterprise Food Delivery Platform

A live-but-safe health probe for a single BaseProvider. Distinct from
ai.services.health_service.AIHealthService (Sprint 2), which only inspects
configuration state and never calls a provider. ProviderHealthChecker DOES
call provider.complete() - but every Sprint 2 prepared adapter
(OpenAI/Anthropic/Azure OpenAI/Ollama) still guarantees complete() never
performs a real network/SDK call this sprint (it raises immediately), and
MockAIProvider's complete() never leaves the process either - so probing
through this checker is safe regardless of which provider is selected.
"""

import time
from dataclasses import dataclass
from typing import Iterable, List

from app.core.logging_config import get_logger

from ai.core.exceptions import AIServiceError
from ai.providers.base import BaseProvider

logger = get_logger("ai.providers.health")

_PROBE_PROMPT = "healthcheck"


@dataclass(frozen=True)
class ProviderHealthResult:
    """Result of a single live probe against one provider."""

    provider: str
    configured: bool
    reachable: bool
    latency_ms: float
    error: str = ""


class ProviderHealthChecker:
    """Stateless - safe to share as a process-lifetime singleton."""

    async def check(self, provider: BaseProvider) -> ProviderHealthResult:
        """Probes a single provider. If the provider is not configured, no
        call is attempted (reachable=False, error explains why). If it is
        configured, calls complete() with a fixed probe prompt and reports
        whether that call succeeded, without ever raising itself - failures
        are captured in the returned result."""
        if not provider.is_configured():
            logger.info("Provider health probe skipped - not configured", extra={"ctx_provider_name": provider.name})
            return ProviderHealthResult(
                provider=provider.name,
                configured=False,
                reachable=False,
                latency_ms=0.0,
                error="Provider is not configured.",
            )

        start = time.monotonic()
        try:
            await provider.complete(_PROBE_PROMPT)
        except AIServiceError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "Provider health probe failed",
                extra={"ctx_provider_name": provider.name, "ctx_error": str(exc)},
            )
            return ProviderHealthResult(
                provider=provider.name,
                configured=True,
                reachable=False,
                latency_ms=round(latency_ms, 2),
                error=str(exc),
            )

        latency_ms = (time.monotonic() - start) * 1000
        logger.info(
            "Provider health probe succeeded",
            extra={"ctx_provider_name": provider.name, "ctx_latency_ms": round(latency_ms, 2)},
        )
        return ProviderHealthResult(
            provider=provider.name, configured=True, reachable=True, latency_ms=round(latency_ms, 2)
        )

    async def check_all(self, providers: Iterable[BaseProvider]) -> List[ProviderHealthResult]:
        """Probes every given provider in turn. Sequential by design - this
        sprint has no requirement for concurrent probing, and sequential
        keeps the log ordering easy to follow."""
        return [await self.check(provider) for provider in providers]

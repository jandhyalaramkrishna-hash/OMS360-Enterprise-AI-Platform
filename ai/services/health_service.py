"""
AI Service Layer - Services - Health service
OMS-360 Enterprise Food Delivery Platform

Verifies provider configuration, runtime configuration, and feature
flags, and reports a structured health status. Performs no network call
and executes no provider, RAG, MCP, or agent action.
"""

from dataclasses import dataclass

from app.core.logging_config import get_logger

from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult

logger = get_logger("ai.services.health")


@dataclass(frozen=True)
class AIHealthReport:
    healthy: bool
    ai_enabled: bool
    configured_providers: list
    unconfigured_providers: list
    feature_flags: dict
    errors: list
    warnings: list


class AIHealthService:
    """Constructed via ServiceFactory.build_health_service(), not directly.
    `healthy` reflects "no configuration errors" - it is not the same as
    AIServiceStatus.is_operational, which additionally requires AI to be
    enabled and a provider to be configured."""

    def __init__(
        self,
        runtime_config: RuntimeConfiguration,
        validation: ValidationResult,
        provider_registry: ProviderRegistry,
    ):
        self._runtime_config = runtime_config
        self._validation = validation
        self._provider_registry = provider_registry

    def check(self) -> AIHealthReport:
        configured = self._provider_registry.list_configured_providers()
        all_providers = self._provider_registry.list_providers()
        unconfigured = sorted(set(all_providers) - set(configured))

        report = AIHealthReport(
            healthy=not self._validation.errors,
            ai_enabled=self._runtime_config.ai_enabled,
            configured_providers=configured,
            unconfigured_providers=unconfigured,
            feature_flags=dict(self._runtime_config.feature_flags),
            errors=list(self._validation.errors),
            warnings=list(self._validation.warnings),
        )
        logger.info(
            "AI health check performed",
            extra={"ctx_healthy": report.healthy, "ctx_configured_provider_count": len(configured)},
        )
        return report

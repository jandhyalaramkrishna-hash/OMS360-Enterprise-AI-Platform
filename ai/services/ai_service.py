"""
AI Service Layer - Services - AIService
OMS-360 Enterprise Food Delivery Platform

The top-level façade for the AI Service Layer: composes the Sprint 1
primitives (tool registry, agent orchestrator, eval runner, prompt
loader remain reachable via ai/dependencies.py) with the Sprint 2
runtime configuration and provider registry. Sprint 2 scope: AIService
correctly reports its own availability/capability state; it does not
perform any real RAG retrieval, agent execution, MCP tool execution, or
provider call.
"""

from dataclasses import dataclass

from app.core.logging_config import get_logger

from ai.core.exceptions import AIFeatureDisabledError, AIProviderNotConfiguredError
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult

logger = get_logger("ai.services.ai_service")


@dataclass(frozen=True)
class AIServiceStatus:
    ai_enabled: bool
    capability_flags: dict
    configured_providers: list
    validation_errors: list
    validation_warnings: list

    @property
    def is_operational(self) -> bool:
        """True only if AI is enabled, at least one provider is
        configured, and there are no validation errors. This is stricter
        than "healthy" (see AIHealthService), which only checks for
        configuration errors."""
        return self.ai_enabled and bool(self.configured_providers) and not self.validation_errors


class AIService:
    """Constructed via ServiceFactory.build_ai_service(), not directly."""

    def __init__(
        self,
        runtime_config: RuntimeConfiguration,
        validation: ValidationResult,
        provider_registry: ProviderRegistry,
    ):
        self._runtime_config = runtime_config
        self._validation = validation
        self._provider_registry = provider_registry
        logger.info(
            "AIService initialized",
            extra={
                "ctx_ai_enabled": runtime_config.ai_enabled,
                "ctx_configured_provider_count": len(provider_registry.list_configured_providers()),
            },
        )

    def status(self) -> AIServiceStatus:
        return AIServiceStatus(
            ai_enabled=self._runtime_config.ai_enabled,
            capability_flags=dict(self._runtime_config.feature_flags),
            configured_providers=self._provider_registry.list_configured_providers(),
            validation_errors=list(self._validation.errors),
            validation_warnings=list(self._validation.warnings),
        )

    def require_capability(self, flag_name: str) -> None:
        """Raises AIFeatureDisabledError unless the given capability flag
        (and the master AI_ENABLED flag) are both true. Future real
        RAG/MCP/Agents work should call this as a guard before running."""
        if not self._runtime_config.is_capability_enabled(flag_name):
            raise AIFeatureDisabledError(flag_name)

    def get_selected_provider(self):
        """Returns the BaseProvider matching runtime_config.provider_name
        (AI_PROVIDER_NAME/AI_PROVIDER). Raises AIProviderNotConfiguredError
        if no provider is selected, or AIProviderNotFoundError (via the
        registry) if the selected name isn't registered."""
        if not self._runtime_config.provider_name:
            raise AIProviderNotConfiguredError(
                "No AI provider is selected (AI_PROVIDER_NAME/AI_PROVIDER unset)."
            )
        return self._provider_registry.get_provider(self._runtime_config.provider_name)

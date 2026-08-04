"""
AI Service Layer - Providers - Provider factory (Sprint 4)
OMS-360 Enterprise Food Delivery Platform

Owns the mapping from provider name -> provider class, so callers never
hardcode "which provider classes exist" themselves. Before Sprint 4 that
list lived inline inside ai.services.factory.ServiceFactory
(_KNOWN_PROVIDER_CLASSES); it has moved here so provider *construction* is
a single-responsibility concern, separate from ServiceFactory's job of
composing higher-level services (AIService/AIHealthService/AIChatService).

Adds MockAIProvider (Sprint 4) alongside the four Sprint 2
prepared-but-never-called adapters (OpenAI, Anthropic, Azure OpenAI,
Ollama). Still none of the four make a network call; MockAIProvider is the
only provider whose complete() actually returns a (simulated) result.
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderNotFoundError
from ai.providers.anthropic_provider import AnthropicProvider
from ai.providers.azure_openai_provider import AzureOpenAIProvider
from ai.providers.base import BaseProvider
from ai.providers.mock_provider import MockAIProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.openai_provider import OpenAIProvider
from ai.providers.registry import ProviderRegistry

logger = get_logger("ai.providers.factory")

_PROVIDER_CLASSES = (
    OpenAIProvider,
    AnthropicProvider,
    AzureOpenAIProvider,
    OllamaProvider,
    MockAIProvider,
)

_PROVIDER_CLASSES_BY_NAME = {cls.name: cls for cls in _PROVIDER_CLASSES}


class ProviderFactory:
    """Single Responsibility: constructs BaseProvider instances by name.
    Does not decide which provider is *selected* at runtime - that remains
    RuntimeConfiguration.provider_name / AIService.get_selected_provider().
    Holds no state itself; every method is a pure construction helper, safe
    to call from anywhere without a shared instance."""

    @staticmethod
    def known_provider_names() -> list:
        """Every provider name this factory knows how to construct,
        regardless of whether it is currently configured."""
        return sorted(_PROVIDER_CLASSES_BY_NAME.keys())

    @staticmethod
    def create(name: str) -> BaseProvider:
        """Constructs a single provider by name. Raises
        AIProviderNotFoundError (404) if the name isn't one this factory
        knows how to build - the same exception ProviderRegistry.get_provider
        raises for an unregistered name, so callers get one consistent
        error type regardless of which layer rejected the name."""
        provider_cls = _PROVIDER_CLASSES_BY_NAME.get(name)
        if provider_cls is None:
            raise AIProviderNotFoundError(name)
        return provider_cls()

    @staticmethod
    def create_all() -> list:
        """Instantiates one instance of every known provider class, in a
        stable, deterministic order."""
        return [provider_cls() for provider_cls in _PROVIDER_CLASSES]

    @staticmethod
    def build_registry() -> ProviderRegistry:
        """Builds a ProviderRegistry with every known provider registered.
        Replaces the Sprint 2 hardcoded tuple that used to live directly
        inside ai.services.factory.ServiceFactory.build_provider_registry()."""
        registry = ProviderRegistry()
        for provider in ProviderFactory.create_all():
            registry.register(provider)
        logger.info(
            "ProviderRegistry built via ProviderFactory",
            extra={"ctx_provider_count": len(registry.list_providers())},
        )
        return registry

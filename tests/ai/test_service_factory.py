"""
Tests for ai/services/factory.py — ServiceFactory builds correctly-wired
AIService / AIHealthService / AIChatService / ProviderRegistry instances.

Sprint 4: ServiceFactory.build_provider_registry() now delegates to
ai.providers.factory.ProviderFactory, which registers a fifth provider,
"mock" (MockAIProvider), alongside the four Sprint 2 adapters - updated
here from the Sprint 2 four-provider expectation.
"""

from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService
from ai.services.factory import ServiceFactory
from ai.services.health_service import AIHealthService


def test_build_provider_registry_registers_all_five_known_providers():
    registry = ServiceFactory.build_provider_registry()
    assert registry.list_providers() == ["anthropic", "azure_openai", "mock", "ollama", "openai"]


def test_build_ai_service_returns_ai_service_instance():
    service = ServiceFactory.build_ai_service()
    assert isinstance(service, AIService)
    status = service.status()
    assert isinstance(status.configured_providers, list)


def test_build_health_service_returns_health_service_instance():
    health_service = ServiceFactory.build_health_service()
    assert isinstance(health_service, AIHealthService)
    report = health_service.check()
    assert isinstance(report.configured_providers, list)
    assert set(report.configured_providers) | set(report.unconfigured_providers) == {
        "openai", "anthropic", "azure_openai", "ollama", "mock",
    }
    # "mock" is always self-configured by design (Sprint 4) - unlike the
    # four Sprint 2 adapters, which are unconfigured by default in a test
    # environment with no provider env vars set.
    assert "mock" in report.configured_providers


def test_build_chat_service_returns_chat_service_instance():
    chat_service = ServiceFactory.build_chat_service()
    assert isinstance(chat_service, AIChatService)

"""
Tests for the Sprint 4 additions to ai/dependencies.py — get_chat_service,
get_provider_health_checker, and that the chat service shares the same
provider registry / AI service singletons as the Sprint 2 additions.
"""

from ai.dependencies import (
    get_ai_service,
    get_chat_service,
    get_provider_health_checker,
    get_provider_registry,
)
from ai.providers.health import ProviderHealthChecker
from ai.services.chat_service import AIChatService


def test_sprint4_providers_return_singletons():
    assert get_chat_service() is get_chat_service()
    assert get_provider_health_checker() is get_provider_health_checker()


def test_get_chat_service_returns_chat_service_instance():
    assert isinstance(get_chat_service(), AIChatService)


def test_get_provider_health_checker_returns_health_checker_instance():
    assert isinstance(get_provider_health_checker(), ProviderHealthChecker)


def test_chat_service_shares_the_same_provider_registry_as_ai_service():
    assert get_chat_service()._provider_registry is get_provider_registry()


def test_chat_service_shares_the_same_ai_service_singleton():
    assert get_chat_service()._ai_service is get_ai_service()


def test_provider_registry_includes_mock_provider():
    assert "mock" in get_provider_registry().list_providers()

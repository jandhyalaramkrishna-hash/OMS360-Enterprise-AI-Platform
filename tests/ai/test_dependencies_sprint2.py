"""
Tests for the Sprint 2 additions to ai/dependencies.py — get_ai_service,
get_ai_health_service, get_provider_registry, get_ai_metrics.
"""

from ai.dependencies import (
    get_ai_health_service,
    get_ai_metrics,
    get_ai_service,
    get_provider_registry,
)
from ai.services.ai_service import AIService
from ai.services.health_service import AIHealthService


def test_sprint2_providers_return_singletons():
    assert get_provider_registry() is get_provider_registry()
    assert get_ai_service() is get_ai_service()
    assert get_ai_health_service() is get_ai_health_service()
    assert get_ai_metrics() is get_ai_metrics()


def test_ai_service_and_health_service_share_the_same_provider_registry():
    assert get_ai_service()._provider_registry is get_provider_registry()
    assert get_ai_health_service()._provider_registry is get_provider_registry()


def test_get_ai_service_returns_ai_service_instance():
    assert isinstance(get_ai_service(), AIService)


def test_get_ai_health_service_returns_health_service_instance():
    assert isinstance(get_ai_health_service(), AIHealthService)

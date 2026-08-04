"""
Tests for ai/services/ai_service.py — AIService status reporting,
capability gating, and provider selection.
"""

import pytest

from ai.core.exceptions import AIFeatureDisabledError, AIProviderNotConfiguredError
from ai.core.exceptions import AIProviderNotFoundError
from ai.providers.base import BaseProvider
from ai.providers.registry import ProviderRegistry
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import ValidationResult
from ai.services.ai_service import AIService


class _FakeProvider(BaseProvider):
    def __init__(self, name, configured=True):
        self.name = name
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    async def complete(self, prompt: str, **kwargs) -> dict:
        raise NotImplementedError


def _runtime_config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    return RuntimeConfiguration(**base)


def test_status_reflects_disabled_default_state():
    service = AIService(_runtime_config(), ValidationResult(), ProviderRegistry())
    status = service.status()
    assert status.ai_enabled is False
    assert status.configured_providers == []
    assert status.is_operational is False


def test_status_is_operational_when_enabled_configured_and_no_errors():
    registry = ProviderRegistry()
    registry.register(_FakeProvider("openai", configured=True))
    service = AIService(
        _runtime_config(ai_enabled=True, provider_name="openai", provider_api_key_configured=True),
        ValidationResult(),
        registry,
    )
    assert service.status().is_operational is True


def test_status_not_operational_with_validation_errors_even_if_enabled():
    registry = ProviderRegistry()
    registry.register(_FakeProvider("openai", configured=True))
    validation = ValidationResult(errors=["something is wrong"])
    service = AIService(_runtime_config(ai_enabled=True), validation, registry)
    assert service.status().is_operational is False


def test_require_capability_raises_when_disabled():
    service = AIService(_runtime_config(), ValidationResult(), ProviderRegistry())
    with pytest.raises(AIFeatureDisabledError):
        service.require_capability("rag_enabled")


def test_require_capability_passes_when_enabled():
    config = _runtime_config(ai_enabled=True, feature_flags={"rag_enabled": True})
    service = AIService(config, ValidationResult(), ProviderRegistry())
    service.require_capability("rag_enabled")  # should not raise


def test_get_selected_provider_raises_when_none_selected():
    service = AIService(_runtime_config(), ValidationResult(), ProviderRegistry())
    with pytest.raises(AIProviderNotConfiguredError):
        service.get_selected_provider()


def test_get_selected_provider_raises_when_selected_name_not_registered():
    service = AIService(_runtime_config(provider_name="openai"), ValidationResult(), ProviderRegistry())
    with pytest.raises(AIProviderNotFoundError):
        service.get_selected_provider()


def test_get_selected_provider_returns_registered_provider():
    registry = ProviderRegistry()
    provider = _FakeProvider("openai")
    registry.register(provider)
    service = AIService(_runtime_config(provider_name="openai"), ValidationResult(), registry)
    assert service.get_selected_provider() is provider

"""
Tests for ai/copilot/provider_manager.py — AIProviderManager's AUTO
selection policy (OpenAI -> Anthropic -> Ollama -> Azure OpenAI ->
none_configured), against the real ProviderRegistry/provider adapters
(no mocking of ai.providers.* itself — only environment variables are
manipulated, exactly like tests/ai/test_provider_registry.py already
does for the underlying registry).
"""

import pytest

from ai.copilot.provider_manager import AIProviderManager, ProviderSelection
from ai.providers.factory import ProviderFactory
from ai.providers.registry import ProviderRegistry


@pytest.fixture()
def registry():
    # Built via ProviderFactory.build_registry(), the same way
    # ai/dependencies.py builds the real shared registry - a bare
    # ProviderRegistry() has nothing registered, which would make every
    # get_provider() lookup fail closed regardless of env vars.
    return ProviderFactory.build_registry()


def test_auto_with_nothing_configured_reports_none_configured(registry, monkeypatch):
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    manager = AIProviderManager(registry)
    selection = manager.get_active_provider()
    assert selection.source == "none_configured"
    assert selection.provider is None
    assert selection.provider_name is None
    assert selection.reasoning_available is False


def test_auto_prefers_openai_when_multiple_configured(registry, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test")
    manager = AIProviderManager(registry)
    selection = manager.get_active_provider()
    assert selection.source == "auto"
    assert selection.provider_name == "openai"
    assert selection.reasoning_available is True


def test_auto_falls_through_to_anthropic_when_openai_unconfigured(registry, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test")
    manager = AIProviderManager(registry)
    selection = manager.get_active_provider()
    assert selection.source == "auto"
    assert selection.provider_name == "anthropic"


def test_explicit_provider_name_wins_over_auto(registry, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test")
    manager = AIProviderManager(registry, explicit_provider_name="anthropic")
    selection = manager.get_active_provider()
    assert selection.source == "explicit"
    assert selection.provider_name == "anthropic"


def test_explicit_unconfigured_provider_falls_back_to_auto(registry, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    manager = AIProviderManager(registry, explicit_provider_name="anthropic")
    selection = manager.get_active_provider()
    assert selection.source == "auto"
    assert selection.provider_name == "openai"


def test_explicit_mock_is_ignored_never_treated_as_a_real_provider(registry, monkeypatch):
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    manager = AIProviderManager(registry, explicit_provider_name="mock")
    selection = manager.get_active_provider()
    assert selection.source == "none_configured"
    assert selection.provider is None


def test_status_shape(registry):
    manager = AIProviderManager(registry)
    status = manager.status()
    assert set(status.keys()) == {"active_provider", "source", "reasoning_available", "checked_providers"}
    assert "mock" not in status["checked_providers"]


def test_provider_selection_provider_name_property_none_when_no_provider():
    selection = ProviderSelection(provider=None, source="none_configured", reasoning_available=False)
    assert selection.provider_name is None

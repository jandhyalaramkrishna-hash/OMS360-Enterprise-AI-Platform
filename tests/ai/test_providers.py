"""
Tests for ai/providers/* — every provider correctly reports its own
configuration state from environment variables, and complete() never
makes a network call: it always raises AIProviderNotConfiguredError.
"""

import asyncio

import pytest

from ai.core.exceptions import AIProviderNotConfiguredError
from ai.providers.anthropic_provider import AnthropicProvider
from ai.providers.azure_openai_provider import AzureOpenAIProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.openai_provider import OpenAIProvider

_ALL_PROVIDER_CLASSES = (OpenAIProvider, AnthropicProvider, AzureOpenAIProvider, OllamaProvider)
_ALL_ENV_VARS = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
    "OLLAMA_BASE_URL",
)


def _clear_env(monkeypatch):
    for var in _ALL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_all_providers_unconfigured_by_default(monkeypatch):
    _clear_env(monkeypatch)
    for provider_cls in _ALL_PROVIDER_CLASSES:
        assert provider_cls().is_configured() is False, provider_cls.name


def test_all_providers_complete_always_raises_never_calls_network(monkeypatch):
    _clear_env(monkeypatch)
    # Even providers with correct config raise, since Sprint 2 makes no
    # real call under any circumstance.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    for provider_cls in _ALL_PROVIDER_CLASSES:
        provider = provider_cls()
        with pytest.raises(AIProviderNotConfiguredError):
            asyncio.run(provider.complete("hello"))


def test_openai_configured_with_api_key(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert OpenAIProvider().is_configured() is True


def test_anthropic_configured_with_api_key(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert AnthropicProvider().is_configured() is True


def test_azure_openai_requires_both_key_and_endpoint(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key-only")
    assert AzureOpenAIProvider().is_configured() is False

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    assert AzureOpenAIProvider().is_configured() is True


def test_ollama_requires_explicit_base_url_no_localhost_default(monkeypatch):
    _clear_env(monkeypatch)
    assert OllamaProvider().is_configured() is False
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    assert OllamaProvider().is_configured() is True


def test_provider_names_are_unique():
    names = [p.name for p in (cls() for cls in _ALL_PROVIDER_CLASSES)]
    assert len(names) == len(set(names))

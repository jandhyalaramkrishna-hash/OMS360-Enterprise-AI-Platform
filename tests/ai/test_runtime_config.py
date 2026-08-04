"""
Tests for ai/runtime/config.py — environment-variable-native runtime
configuration (Sprint 2). Uses monkeypatch so tests never depend on, or
mutate, the real process environment or any .env file.
"""

from ai.runtime.config import RuntimeConfiguration, load_runtime_configuration

_ENV_VARS = (
    "AI_ENABLED", "RAG_ENABLED", "MCP_ENABLED", "AGENTS_ENABLED", "EVALS_ENABLED",
    "AI_PROVIDER_NAME", "AI_PROVIDER", "AI_API_KEY",
)


def _clear_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_are_fully_disabled(monkeypatch):
    _clear_env(monkeypatch)
    config = load_runtime_configuration()
    assert config.ai_enabled is False
    assert config.rag_enabled is False
    assert config.mcp_enabled is False
    assert config.agents_enabled is False
    assert config.evals_enabled is False
    assert config.provider_name == ""
    assert config.provider_api_key_configured is False


def test_true_values_recognized(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("RAG_ENABLED", "1")
    monkeypatch.setenv("MCP_ENABLED", "YES")
    monkeypatch.setenv("AGENTS_ENABLED", "On")
    config = load_runtime_configuration()
    assert config.ai_enabled is True
    assert config.rag_enabled is True
    assert config.mcp_enabled is True
    assert config.agents_enabled is True
    assert config.evals_enabled is False


def test_provider_name_prefers_ai_provider_name_over_ai_provider(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AI_PROVIDER_NAME", "openai")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    config = load_runtime_configuration()
    assert config.provider_name == "openai"


def test_provider_name_falls_back_to_ai_provider(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    config = load_runtime_configuration()
    assert config.provider_name == "anthropic"


def test_api_key_configured_flag(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AI_API_KEY", "sk-test-123")
    config = load_runtime_configuration()
    assert config.provider_api_key_configured is True


def test_is_capability_enabled_requires_both_master_and_own_flag():
    config = RuntimeConfiguration(
        ai_enabled=False, rag_enabled=True, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="openai", provider_api_key_configured=True,
        feature_flags={"rag_enabled": True},
    )
    assert config.is_capability_enabled("rag_enabled") is False

    config2 = RuntimeConfiguration(
        ai_enabled=True, rag_enabled=True, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="openai", provider_api_key_configured=True,
        feature_flags={"rag_enabled": True},
    )
    assert config2.is_capability_enabled("rag_enabled") is True

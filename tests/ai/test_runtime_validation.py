"""
Tests for ai/runtime/validation.py — non-fatal validation of a
RuntimeConfiguration.
"""

from ai.runtime.config import RuntimeConfiguration
from ai.runtime.validation import validate_runtime_configuration


def _config(**overrides):
    base = dict(
        ai_enabled=False, rag_enabled=False, mcp_enabled=False, agents_enabled=False, evals_enabled=False,
        provider_name="", provider_api_key_configured=False,
        feature_flags={"rag_enabled": False, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False},
    )
    base.update(overrides)
    return RuntimeConfiguration(**base)


def test_default_disabled_state_has_no_errors_or_warnings():
    result = validate_runtime_configuration(_config())
    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []


def test_ai_enabled_without_provider_is_an_error():
    result = validate_runtime_configuration(_config(ai_enabled=True))
    assert result.is_valid is False
    assert any("provider" in e.lower() for e in result.errors)


def test_ai_enabled_without_api_key_is_an_error():
    result = validate_runtime_configuration(_config(ai_enabled=True, provider_name="openai"))
    assert result.is_valid is False
    assert any("api_key" in e.lower() or "api key" in e.lower() for e in result.errors)


def test_ai_enabled_with_provider_and_key_has_no_errors():
    result = validate_runtime_configuration(
        _config(ai_enabled=True, provider_name="openai", provider_api_key_configured=True)
    )
    assert result.is_valid is True
    assert result.errors == []


def test_capability_flag_on_while_ai_disabled_is_a_warning_not_error():
    result = validate_runtime_configuration(
        _config(feature_flags={"rag_enabled": True, "mcp_enabled": False, "agents_enabled": False, "evals_enabled": False})
    )
    assert result.is_valid is True
    assert len(result.warnings) == 1
    assert "rag_enabled" in result.warnings[0]


# --- Sprint 4: "mock" is exempt from the AI_API_KEY requirement ------------

def test_ai_enabled_with_mock_provider_does_not_require_api_key():
    result = validate_runtime_configuration(
        _config(ai_enabled=True, provider_name="mock", provider_api_key_configured=False)
    )
    assert result.is_valid is True
    assert result.errors == []


def test_ai_enabled_with_mock_provider_still_requires_a_provider_name():
    # provider_name blank still errors, even though "mock" itself would be
    # exempt from the api-key check - the two checks are independent.
    result = validate_runtime_configuration(_config(ai_enabled=True, provider_name=""))
    assert result.is_valid is False


def test_mock_exemption_matches_the_real_mock_provider_name():
    """Drift guard: ai.runtime.validation hardcodes "mock" as a plain
    string (to avoid ai.runtime depending on ai.providers) - this test
    fails loudly if ai.providers.mock_provider.MockAIProvider.name ever
    changes without validation.py being updated to match."""
    from ai.providers.mock_provider import MockAIProvider

    result = validate_runtime_configuration(
        _config(ai_enabled=True, provider_name=MockAIProvider.name, provider_api_key_configured=False)
    )
    assert result.is_valid is True

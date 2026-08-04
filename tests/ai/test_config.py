"""
Tests for ai/config.py — feature-flag resolution.
"""

from ai.config import AISettings


def test_capability_disabled_when_master_flag_off():
    settings = AISettings(
        master_enabled=False,
        provider="", model_name="", api_key_configured=False,
        capability_flags={"rag_enabled": True},
    )
    assert settings.is_capability_enabled("rag_enabled") is False


def test_capability_disabled_when_own_flag_off():
    settings = AISettings(
        master_enabled=True,
        provider="", model_name="", api_key_configured=False,
        capability_flags={"rag_enabled": False},
    )
    assert settings.is_capability_enabled("rag_enabled") is False


def test_capability_enabled_when_both_flags_on():
    settings = AISettings(
        master_enabled=True,
        provider="openai", model_name="gpt-x", api_key_configured=True,
        capability_flags={"rag_enabled": True},
    )
    assert settings.is_capability_enabled("rag_enabled") is True


def test_unknown_capability_defaults_disabled():
    settings = AISettings(
        master_enabled=True,
        provider="", model_name="", api_key_configured=False,
        capability_flags={},
    )
    assert settings.is_capability_enabled("nonexistent_flag") is False


def test_get_ai_settings_reflects_default_baseline_state():
    """As of Sprint 1, app/config.py ships with ai_features_enabled=False
    and no AI_PROVIDER/AI_API_KEY configured — this test locks in that
    expected, currently-disabled baseline so a future change is visible."""
    from ai.config import get_ai_settings

    settings = get_ai_settings()
    assert settings.master_enabled is False
    assert settings.api_key_configured is False
    assert all(v is False for v in settings.capability_flags.values())

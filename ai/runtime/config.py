"""
AI Service Layer - Runtime Configuration
OMS-360 Enterprise Food Delivery Platform

Sprint 2: environment-variable-native runtime configuration for the AI
Service Layer (AIService, provider framework, health checks, metrics).

This is additive to, not a replacement for, ai/config.py's AISettings
(Sprint 1) - that file is untouched and remains valid for existing
callers (e.g. ai.dependencies.require_ai_enabled). This module reads
AI_ENABLED / RAG_ENABLED / MCP_ENABLED / AGENTS_ENABLED / EVALS_ENABLED
directly from the environment (via python-dotenv, already an existing
project dependency), independent of app/config.py, keeping the AI
Service Layer's Sprint 2 runtime configuration fully self-contained. See
ai/README.md for why two flag surfaces exist and how they relate.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()  # idempotent - does not override already-set env vars;
                # ensures ai/ can resolve its own configuration even if
                # app/ hasn't loaded a .env file yet in this process.

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class RuntimeConfiguration:
    """An immutable snapshot of the AI Service Layer's Sprint 2 runtime
    configuration. Build via load_runtime_configuration(), not directly."""

    ai_enabled: bool
    rag_enabled: bool
    mcp_enabled: bool
    agents_enabled: bool
    evals_enabled: bool
    provider_name: str
    provider_api_key_configured: bool
    feature_flags: dict = field(default_factory=dict)
    # AI Copilot addition (new line, DEC-0033 onward): deliberately its
    # own top-level field, NOT folded into feature_flags/
    # is_capability_enabled(). Every existing capability flag above is
    # AND-ed with the master ai_enabled flag by design (Sprint 1-9
    # assumed "AI capability" always means "calls a provider"). AI
    # Copilot's Business Q&A/Executive Summary/Business Insights work
    # completely without any provider configured (see
    # ai/copilot/__init__.py), so gating them behind ai_enabled - which
    # defaults false and requires an AI_API_KEY to avoid a validation
    # error - would make the one AI feature meant to work out of the box
    # invisible by default. copilot_enabled defaults True and is checked
    # on its own, independent of ai_enabled.
    copilot_enabled: bool = True

    def is_capability_enabled(self, flag_name: str) -> bool:
        """A capability is enabled only if the master AI_ENABLED flag AND
        its own flag are both true. flag_name is one of "rag_enabled",
        "mcp_enabled", "agents_enabled", "evals_enabled". Does NOT apply
        to copilot_enabled - see that field's docstring for why."""
        return self.ai_enabled and bool(self.feature_flags.get(flag_name, False))


def load_runtime_configuration() -> RuntimeConfiguration:
    """Reads AI_ENABLED, RAG_ENABLED, MCP_ENABLED, AGENTS_ENABLED,
    EVALS_ENABLED, COPILOT_ENABLED, and the selected provider name / API
    key presence from the environment. Every flag except COPILOT_ENABLED
    defaults to disabled/empty (fail-closed, matching ai/config.py's
    Sprint 1 default); COPILOT_ENABLED defaults to True (see
    RuntimeConfiguration.copilot_enabled's docstring)."""
    feature_flags = {
        "rag_enabled": _env_bool("RAG_ENABLED"),
        "mcp_enabled": _env_bool("MCP_ENABLED"),
        "agents_enabled": _env_bool("AGENTS_ENABLED"),
        "evals_enabled": _env_bool("EVALS_ENABLED"),
    }
    return RuntimeConfiguration(
        ai_enabled=_env_bool("AI_ENABLED"),
        rag_enabled=feature_flags["rag_enabled"],
        mcp_enabled=feature_flags["mcp_enabled"],
        agents_enabled=feature_flags["agents_enabled"],
        evals_enabled=feature_flags["evals_enabled"],
        provider_name=(os.environ.get("AI_PROVIDER_NAME") or os.environ.get("AI_PROVIDER") or "").strip(),
        provider_api_key_configured=bool(os.environ.get("AI_API_KEY", "").strip()),
        feature_flags=feature_flags,
        copilot_enabled=_env_bool("COPILOT_ENABLED", default=True),
    )

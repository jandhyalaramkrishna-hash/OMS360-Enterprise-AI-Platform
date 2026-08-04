"""
AI Service Layer - Configuration
OMS-360 Enterprise Food Delivery Platform

Single seam between the isolated `ai/` package and the existing OMS360
application config (`app/config.py`). This is the ONLY file in `ai/` that
imports from `app.config` - every other module in this package reaches
settings through this file, never directly.

Feature flags are intentionally granular: the existing master switch
`FEATURE_FLAGS["ai_features_enabled"]` in app/config.py is the top-level
kill switch (must be True for ANY AI capability to run), and each AI
capability additionally has its own flag defined here, defaulting to
False, so individual capabilities (RAG, MCP, Agents, Evals, Prompts) can
be enabled independently once they have real implementations behind them.
None of these granular flags are read from app/config.py - they live here
so enabling/disabling a specific AI capability never requires touching the
existing OMS360 config file.
"""

from dataclasses import dataclass, field

from app.config import settings

# Granular, per-capability flags. All default False - enabling any of
# these before a real provider/implementation exists behind it should be
# a deliberate, later decision, not a side effect of this file existing.
AI_FEATURE_FLAGS: dict = {
    "rag_enabled": False,
    "mcp_enabled": False,
    "agents_enabled": False,
    "evals_enabled": False,
    "prompts_enabled": False,
}


@dataclass(frozen=True)
class AISettings:
    """Read-only view over AI-relevant configuration. Construct via
    get_ai_settings() rather than instantiating directly, so there is a
    single source of truth for how these values are derived."""

    master_enabled: bool
    provider: str
    model_name: str
    api_key_configured: bool
    capability_flags: dict = field(default_factory=dict)

    def is_capability_enabled(self, capability: str) -> bool:
        """A capability is enabled only if BOTH the master switch and its
        own granular flag are True. `capability` must be one of the keys
        in AI_FEATURE_FLAGS (e.g. "rag_enabled")."""
        return self.master_enabled and bool(self.capability_flags.get(capability, False))


def get_ai_settings() -> AISettings:
    """Builds an AISettings snapshot from the existing app.config.settings
    plus this module's granular flags. Never logs or exposes the raw API
    key - only whether one is configured."""
    return AISettings(
        master_enabled=bool(settings.FEATURE_FLAGS.get("ai_features_enabled", False)),
        provider=getattr(settings, "AI_PROVIDER", "") or "",
        model_name=getattr(settings, "AI_MODEL_NAME", "") or "",
        api_key_configured=bool(getattr(settings, "AI_API_KEY", "") or ""),
        capability_flags=dict(AI_FEATURE_FLAGS),
    )

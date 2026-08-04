"""
AI Service Layer - Runtime Configuration Validation
OMS-360 Enterprise Food Delivery Platform
"""

from dataclasses import dataclass, field

from ai.runtime.config import RuntimeConfiguration

# Sprint 4: provider names that legitimately need no AI_API_KEY. Currently
# just "mock" (ai.providers.mock_provider.MockAIProvider.name) - it is
# always self-configured by design, unlike every hosted/networked provider.
# Kept as a plain string constant (rather than importing MockAIProvider
# here) to avoid ai.runtime depending on ai.providers; see
# tests/ai/test_runtime_validation.py for a drift-check against the real
# provider name.
_NO_API_KEY_REQUIRED_PROVIDERS = {"mock"}


@dataclass
class ValidationResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_runtime_configuration(config: RuntimeConfiguration) -> ValidationResult:
    """Non-fatal validation: returns a report rather than raising, so
    callers (e.g. the health service) can surface configuration problems
    without crashing. AI_ENABLED with no provider selected is an ERROR
    (nothing could actually run once wired up); AI_ENABLED with a provider
    selected but no AI_API_KEY is also an ERROR, unless that provider is in
    _NO_API_KEY_REQUIRED_PROVIDERS (Sprint 4: "mock" needs no credentials by
    design); a capability flag being on while AI_ENABLED is off is a
    WARNING (inert, harmless)."""
    result = ValidationResult()

    if config.ai_enabled and not config.provider_name:
        result.errors.append(
            "AI_ENABLED is true but no AI provider is selected (AI_PROVIDER_NAME/AI_PROVIDER unset)."
        )
    if (
        config.ai_enabled
        and config.provider_name not in _NO_API_KEY_REQUIRED_PROVIDERS
        and not config.provider_api_key_configured
    ):
        result.errors.append("AI_ENABLED is true but no AI_API_KEY is configured.")

    for flag_name, enabled in config.feature_flags.items():
        if enabled and not config.ai_enabled:
            result.warnings.append(
                f"{flag_name} is true but AI_ENABLED is false - "
                f"this capability will stay inert until AI_ENABLED is also true."
            )

    return result

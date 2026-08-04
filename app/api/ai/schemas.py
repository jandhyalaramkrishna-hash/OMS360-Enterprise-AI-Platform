"""
AI API Layer - Request / Response / Validation / Error models
OMS-360 Enterprise Food Delivery Platform

Sprint 3 scope. All six endpoints in app/api/ai/router.py are GET-only
and read-only - none takes a JSON request body - so there is no
"AI*Request" body model to define here. That's stated explicitly rather
than left silently absent, since the Sprint 3 brief calls for the model
taxonomy to be Request / Response / Validation / Error. The two optional
query parameters that do exist (?capability= on /config, ?name= on
/providers) are validated as described under Validation Models below.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas import ErrorResponse  # noqa: F401  (re-exported - see Error Models at the bottom)


# --- Validation Models -------------------------------------------------------
# ai.runtime.config.RuntimeConfiguration.feature_flags always has exactly
# these four keys (ai/runtime/config.py, Sprint 2) - this constant is the
# single source of truth the /config route validates ?capability=
# against, and is also rendered into that endpoint's Swagger description.

KNOWN_CAPABILITY_FLAGS: tuple = ("rag_enabled", "mcp_enabled", "agents_enabled", "evals_enabled")


class CapabilityQueryParam(BaseModel):
    """Documents the validation rule applied to GET /config?capability=.
    FastAPI's Query(...) enforces min_length directly on the route
    signature (see router.py); this model exists so the rule itself -
    non-blank, and a member of KNOWN_CAPABILITY_FLAGS - is documented and
    unit-testable independently of the route wiring. An unknown value
    (present but not in KNOWN_CAPABILITY_FLAGS) raises
    ai.core.exceptions.AIInvalidCapabilityError (400) from the route."""

    capability: str = Field(..., min_length=1, description=f"One of: {', '.join(KNOWN_CAPABILITY_FLAGS)}.")


class ProviderNameQueryParam(BaseModel):
    """Documents the validation rule applied to GET /providers?name=.
    FastAPI's Query(...) enforces min_length directly on the route
    signature; a name that IS well-formed but unregistered raises
    ai.core.exceptions.AIProviderNotFoundError (404), which already
    existed from Sprint 2 - no new exception was needed for that case."""

    name: str = Field(..., min_length=1, description="Registered provider name, e.g. 'openai'.")


# --- Response Models ---------------------------------------------------------

class AIHealthResponse(BaseModel):
    healthy: bool = Field(..., description="True only if the AI Runtime configuration has no validation errors.")
    ai_enabled: bool
    configured_providers: List[str]
    unconfigured_providers: List[str]
    feature_flags: Dict[str, bool]
    errors: List[str]
    warnings: List[str]


class AIConfigResponse(BaseModel):
    ai_enabled: bool
    provider_name: str = Field(..., description="Empty string if no provider is selected.")
    provider_api_key_configured: bool = Field(
        ..., description="Whether AI_API_KEY is set in the environment - never the key value itself."
    )
    feature_flags: Dict[str, bool]
    validation_errors: List[str]
    validation_warnings: List[str]
    capability_enabled: Optional[bool] = Field(
        default=None,
        description="Set only when ?capability= was supplied - whether that specific capability is enabled.",
    )


class AIProviderSummary(BaseModel):
    name: str
    configured: bool


class AIProvidersResponse(BaseModel):
    providers: List[AIProviderSummary]
    configured_count: int
    total_count: int


class AIProviderDetailResponse(BaseModel):
    """Returned instead of AIProvidersResponse when ?name= is supplied."""

    name: str
    configured: bool
    required_env_vars: List[str]


class AIFeaturesResponse(BaseModel):
    ai_enabled: bool
    feature_flags: Dict[str, bool]


class AIMetricsResponse(BaseModel):
    request_count: int
    response_count: int
    error_count: int
    token_usage_total: int
    provider_latency_ms: Dict[str, List[float]]


class AIStatusResponse(BaseModel):
    ai_enabled: bool
    is_operational: bool = Field(
        ..., description="True only if AI is enabled, a provider is configured, and there are no validation errors."
    )
    capability_flags: Dict[str, bool]
    configured_providers: List[str]
    validation_errors: List[str]
    validation_warnings: List[str]


# --- Sprint 9 additions (Enterprise Integration: unified platform health) ---
# One additional response model for the one new route Sprint 9 explicitly
# asks for ("Implement a unified health/status endpoint for all AI
# modules"). Each summary model below mirrors the shape of the existing,
# unmodified per-module health result dataclass it's built from
# (ai.providers.health.ProviderHealthResult, ai.mcp.health.ToolHealthResult,
# ai.agents.health.AgentHealthResult) - no new health-check logic is
# introduced here, only a response shape for what ai.integration.health.
# PlatformHealthChecker already reports.

class ProviderHealthSummary(BaseModel):
    provider: str
    configured: bool
    reachable: bool
    latency_ms: float
    error: str = ""


class ToolHealthSummary(BaseModel):
    tool_name: str
    healthy: bool
    error: Optional[str] = None


class AgentHealthSummary(BaseModel):
    agent_name: str
    healthy: bool
    error: Optional[str] = None


class AIPlatformHealthResponse(BaseModel):
    overall_healthy: bool = Field(
        ...,
        description=(
            "True only if the runtime configuration has no validation errors AND every MCP tool AND every "
            "agent passed its live probe. Provider reachability is reported below but does not gate this "
            "value - most providers are expected to be unconfigured."
        ),
    )
    runtime_healthy: bool
    ai_enabled: bool
    feature_flags: Dict[str, bool]
    providers: List[ProviderHealthSummary]
    mcp_tools: List[ToolHealthSummary]
    agents: List[AgentHealthSummary]
    metrics: AIMetricsResponse
    errors: List[str]
    warnings: List[str]


# --- Error Models -------------------------------------------------------------
# Every error response from this API is app.schemas.ErrorResponse -
# {"error", "detail", "request_id"} - produced automatically by the
# existing global exception handler in app/core/exceptions.py, because
# every AI exception in ai/core/exceptions.py subclasses OMSBusinessError.
# No new error handler or error model is defined in this package;
# ErrorResponse is imported above and reused directly in each route's
# `responses={}` mapping in router.py.

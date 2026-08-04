"""
AI API Layer - Routes
OMS-360 Enterprise Food Delivery Platform

Sprint 3 scope: exposes the Sprint 2 AI Runtime (ai.services.AIService,
ai.services.AIHealthService, ai.providers.ProviderRegistry,
ai.runtime.loader.RuntimeConfigLoader, ai.metrics.AIMetrics) through six
read-only endpoints: /health /config /providers /features /metrics
/status, all under prefix /api/v1/ai. Every dependency below is injected
via ai.dependencies (Depends(...)), never imported and called directly -
the same pattern app/routes/orders.py uses for Depends(get_db).

Hard boundary (do not cross in this sprint): no route here may call
AIService.get_selected_provider().complete(...), trigger RAG retrieval,
run an agent, or execute an MCP tool. Every endpoint only reads
already-computed configuration/health/metrics state - zero provider
calls, zero LLM requests, zero Kafka/database access.

Isolation note: this is the first file under app/ that imports from ai/.
Every prior sprint kept that a one-way street (ai/ depends inward on
app/; nothing in app/ imported ai/) - Sprint 3's own objective is to
expose the AI Runtime through FastAPI, which cannot be done without
crossing that boundary from this one, narrow point. Nothing in ai/ was
changed to depend on app/api/, and no other app/ file imports ai/.

Sprint 9 addition: one seventh endpoint, GET /platform/health, exposing
ai.integration.health.PlatformHealthChecker - the one route Sprint 9's
brief explicitly asks for ("a unified health/status endpoint for all AI
modules"). Unlike the six Sprint 3 endpoints above, this one DOES
live-probe (every registered MCP tool and agent), since it composes the
already-existing, already-live MCPHealthChecker/AgentHealthChecker/
ProviderHealthChecker - it does not call a provider's complete() for a
chat, trigger RAG retrieval, or run the Sprint 9 AIWorkflowService, all
of which remain reachable only via ai.dependencies.get_*() and direct
unit/integration tests this sprint, matching how AgentService/
EvaluationService/RAGSearchService/MCPServer were each left HTTP-
unreachable in their own introducing sprint.
"""

from typing import Optional, Union

from fastapi import APIRouter, Depends, Query

from app.core.logging_config import get_logger
from app.schemas import ErrorResponse

from ai.core.exceptions import AIInvalidCapabilityError
from ai.dependencies import (
    get_ai_health_service,
    get_ai_metrics,
    get_ai_service,
    get_config_loader,
    get_platform_health_checker,
    get_provider_registry,
)
from ai.integration.health import PlatformHealthChecker
from ai.metrics import AIMetrics
from ai.providers.registry import ProviderRegistry
from ai.runtime.loader import RuntimeConfigLoader
from ai.services.ai_service import AIService
from ai.services.health_service import AIHealthService

from app.api.ai.schemas import (
    KNOWN_CAPABILITY_FLAGS,
    AIConfigResponse,
    AIFeaturesResponse,
    AIHealthResponse,
    AIMetricsResponse,
    AIPlatformHealthResponse,
    AIProviderDetailResponse,
    AIProvidersResponse,
    AIProviderSummary,
    AgentHealthSummary,
    AIStatusResponse,
    ProviderHealthSummary,
    ToolHealthSummary,
)

logger = get_logger("app.api.ai")

router = APIRouter(prefix="/api/v1/ai", tags=["AI Runtime"])


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="AI Runtime health check",
    description=(
        "Reports whether the AI Runtime's configuration is valid: provider "
        "configuration, runtime configuration (AI_ENABLED / RAG_ENABLED / "
        "MCP_ENABLED / AGENTS_ENABLED / EVALS_ENABLED), and feature flags. "
        "Performs no network call and no provider/RAG/Agent/MCP execution. "
        "`healthy` means 'no configuration errors' - it does NOT mean AI is "
        "enabled or a provider is configured; see /status for that "
        "stricter, operational check."
    ),
    responses={200: {"description": "AI Runtime health report."}},
)
def get_ai_health(health_service: AIHealthService = Depends(get_ai_health_service)) -> AIHealthResponse:
    report = health_service.check()
    return AIHealthResponse(
        healthy=report.healthy,
        ai_enabled=report.ai_enabled,
        configured_providers=report.configured_providers,
        unconfigured_providers=report.unconfigured_providers,
        feature_flags=report.feature_flags,
        errors=report.errors,
        warnings=report.warnings,
    )


@router.get(
    "/config",
    response_model=AIConfigResponse,
    summary="AI Runtime configuration snapshot",
    description=(
        "Returns the loaded Sprint 2 runtime configuration: whether AI is "
        "enabled, the selected provider name, whether an API key is "
        "configured (never the key itself), the four granular feature "
        "flags, and any validation errors/warnings. Pass ?capability= "
        f"(one of: {', '.join(KNOWN_CAPABILITY_FLAGS)}) to additionally "
        "check whether that specific capability is enabled - an unrecognized "
        "capability name returns 400, a blank one returns 422."
    ),
    responses={
        200: {"description": "Runtime configuration snapshot."},
        400: {"model": ErrorResponse, "description": "?capability= is not a recognized capability name."},
        422: {"model": ErrorResponse, "description": "?capability= was supplied but blank."},
    },
)
def get_ai_config(
    capability: Optional[str] = Query(
        default=None, min_length=1, description=f"Optional - one of: {', '.join(KNOWN_CAPABILITY_FLAGS)}."
    ),
    config_loader: RuntimeConfigLoader = Depends(get_config_loader),
) -> AIConfigResponse:
    runtime_config = config_loader.load()
    validation = config_loader.validation()

    capability_enabled = None
    if capability is not None:
        if capability not in KNOWN_CAPABILITY_FLAGS:
            raise AIInvalidCapabilityError(capability, KNOWN_CAPABILITY_FLAGS)
        capability_enabled = runtime_config.is_capability_enabled(capability)

    return AIConfigResponse(
        ai_enabled=runtime_config.ai_enabled,
        provider_name=runtime_config.provider_name,
        provider_api_key_configured=runtime_config.provider_api_key_configured,
        feature_flags=runtime_config.feature_flags,
        validation_errors=validation.errors,
        validation_warnings=validation.warnings,
        capability_enabled=capability_enabled,
    )


@router.get(
    "/providers",
    response_model=Union[AIProvidersResponse, AIProviderDetailResponse],
    summary="List registered AI providers, or look up one by name",
    description=(
        "Lists every provider registered in the Sprint 2 ProviderRegistry "
        "(openai, anthropic, azure_openai, ollama) and whether each is "
        "configured (has the environment variables it needs) - never "
        "whether it has been called, since no provider is ever called in "
        "this sprint. Pass ?name= to look up a single provider's detail "
        "(AIProviderDetailResponse) instead of the full list; an "
        "unregistered name returns 404, a blank one returns 422."
    ),
    responses={
        200: {"description": "Provider list, or one provider's detail if ?name= was given."},
        404: {"model": ErrorResponse, "description": "?name= does not match any registered provider."},
        422: {"model": ErrorResponse, "description": "?name= was supplied but blank."},
    },
)
def get_ai_providers(
    name: Optional[str] = Query(default=None, min_length=1, description="Look up a single provider by name."),
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
):
    if name is not None:
        provider = provider_registry.get_provider(name)  # raises AIProviderNotFoundError -> 404
        return AIProviderDetailResponse(
            name=provider.name,
            configured=provider.is_configured(),
            required_env_vars=list(provider.required_env_vars),
        )

    all_names = provider_registry.list_providers()
    configured_names = set(provider_registry.list_configured_providers())
    providers = [AIProviderSummary(name=n, configured=n in configured_names) for n in all_names]
    return AIProvidersResponse(
        providers=providers, configured_count=len(configured_names), total_count=len(all_names)
    )


@router.get(
    "/features",
    response_model=AIFeaturesResponse,
    summary="AI feature flags",
    description=(
        "Returns the master AI_ENABLED flag and the four granular Sprint 2 "
        "runtime feature flags (rag_enabled, mcp_enabled, agents_enabled, "
        "evals_enabled). A granular flag only takes effect once AI_ENABLED "
        "is also true - see RuntimeConfiguration.is_capability_enabled()."
    ),
)
def get_ai_features(config_loader: RuntimeConfigLoader = Depends(get_config_loader)) -> AIFeaturesResponse:
    runtime_config = config_loader.load()
    return AIFeaturesResponse(ai_enabled=runtime_config.ai_enabled, feature_flags=runtime_config.feature_flags)


@router.get(
    "/metrics",
    response_model=AIMetricsResponse,
    summary="AI Runtime in-process metrics",
    description=(
        "In-memory counters only (request count, response count, error "
        "count, total token usage, per-provider latency samples) - no "
        "external monitoring integration, per Sprint 2 scope. Counters stay "
        "at zero until a future sprint actually calls a provider; this "
        "endpoint reads existing state, it never generates any."
    ),
)
def get_ai_metrics_snapshot(ai_metrics: AIMetrics = Depends(get_ai_metrics)) -> AIMetricsResponse:
    snapshot = ai_metrics.snapshot()
    return AIMetricsResponse(
        request_count=snapshot.request_count,
        response_count=snapshot.response_count,
        error_count=snapshot.error_count,
        token_usage_total=snapshot.token_usage_total,
        provider_latency_ms=snapshot.provider_latency_ms,
    )


@router.get(
    "/status",
    response_model=AIStatusResponse,
    summary="AI Service operational status",
    description=(
        "The strictest of the AI Runtime status views: `is_operational` is "
        "true only if AI is enabled, at least one provider is configured, "
        "AND there are no validation errors "
        "(AIService.status().is_operational)."
    ),
)
def get_ai_status(ai_service: AIService = Depends(get_ai_service)) -> AIStatusResponse:
    status = ai_service.status()
    return AIStatusResponse(
        ai_enabled=status.ai_enabled,
        is_operational=status.is_operational,
        capability_flags=status.capability_flags,
        configured_providers=status.configured_providers,
        validation_errors=status.validation_errors,
        validation_warnings=status.validation_warnings,
    )


# --- Sprint 9 addition (Enterprise Integration: unified platform health) ----
# The one route this sprint's brief explicitly asks for ("Implement a
# unified health/status endpoint for all AI modules"). Unlike every other
# route in this file, this one is async - it live-probes every registered
# MCP tool and agent (ai.integration.health.PlatformHealthChecker composes
# the existing MCPHealthChecker/AgentHealthChecker/ProviderHealthChecker,
# themselves already async) rather than only reading precomputed state.
# Deliberately NOT gated behind require_ai_enabled/require_capability - a
# health report needs to work (and explain what's disabled/misconfigured)
# regardless of whether AI_ENABLED or any granular flag is on, exactly
# like GET /health above already does for the Sprint 2 runtime layer.


@router.get(
    "/platform/health",
    response_model=AIPlatformHealthResponse,
    summary="Unified AI platform health check (Sprint 9)",
    description=(
        "Aggregates health across every AI module built in Sprints 1-8: "
        "runtime configuration (AIHealthService), every registered "
        "provider (ProviderHealthChecker - a live probe), every "
        "registered MCP tool (MCPHealthChecker - a live probe), every "
        "registered mock agent (AgentHealthChecker - a live probe), plus "
        "a snapshot of AIMetrics. `overall_healthy` is true only if the "
        "runtime configuration has no errors AND every MCP tool AND every "
        "agent passed its live probe; provider reachability is reported "
        "but does not gate `overall_healthy`, since most providers are "
        "expected to be unconfigured (mirrors AIHealthService's own "
        "'healthy = no configuration errors' philosophy)."
    ),
    responses={200: {"description": "Unified AI platform health report."}},
)
async def get_ai_platform_health(
    platform_health_checker: PlatformHealthChecker = Depends(get_platform_health_checker),
) -> AIPlatformHealthResponse:
    report = await platform_health_checker.check()
    return AIPlatformHealthResponse(
        overall_healthy=report.overall_healthy,
        runtime_healthy=report.runtime_health.healthy,
        ai_enabled=report.runtime_health.ai_enabled,
        feature_flags=report.runtime_health.feature_flags,
        providers=[
            ProviderHealthSummary(
                provider=r.provider, configured=r.configured, reachable=r.reachable,
                latency_ms=r.latency_ms, error=r.error,
            )
            for r in report.provider_results
        ],
        mcp_tools=[
            ToolHealthSummary(tool_name=r.tool_name, healthy=r.healthy, error=r.error) for r in report.tool_results
        ],
        agents=[
            AgentHealthSummary(agent_name=r.agent_name, healthy=r.healthy, error=r.error)
            for r in report.agent_results
        ],
        metrics=AIMetricsResponse(
            request_count=report.metrics.request_count,
            response_count=report.metrics.response_count,
            error_count=report.metrics.error_count,
            token_usage_total=report.metrics.token_usage_total,
            provider_latency_ms=report.metrics.provider_latency_ms,
        ),
        errors=report.runtime_health.errors,
        warnings=report.runtime_health.warnings,
    )

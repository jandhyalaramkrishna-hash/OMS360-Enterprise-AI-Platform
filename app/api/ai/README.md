# AI API Layer — `app/api/ai/`

**Status (Sprint 3, 2026-07-19): Built and wired into the running application.** This is the first sprint in which anything under `app/` imports from `ai/`, and the first sprint in which `app/main.py` was touched. See `docs/governance/DECISION-LOG.md` DEC-0015 for the full record of that boundary change and why it was necessary.

## Purpose

Exposes the Sprint 2 AI Runtime (`ai/services/`, `ai/providers/`, `ai/runtime/`, `ai/metrics.py`) through six read-only, internal FastAPI endpoints, all under `/api/v1/ai`:

| Method | Path | Wraps |
|---|---|---|
| GET | `/api/v1/ai/health` | `ai.services.health_service.AIHealthService.check()` |
| GET | `/api/v1/ai/config` | `ai.runtime.loader.RuntimeConfigLoader` (+ optional `?capability=` lookup) |
| GET | `/api/v1/ai/providers` | `ai.providers.registry.ProviderRegistry` (+ optional `?name=` lookup) |
| GET | `/api/v1/ai/features` | `ai.runtime.config.RuntimeConfiguration.feature_flags` |
| GET | `/api/v1/ai/metrics` | `ai.metrics.AIMetrics.snapshot()` |
| GET | `/api/v1/ai/status` | `ai.services.ai_service.AIService.status()` |

## Hard boundary (Sprint 3 scope)

No route in this package may call a provider, perform an LLM request, trigger RAG retrieval, run an agent, or execute an MCP tool. Every endpoint only reads already-computed configuration/health/metrics state. No Kafka, database, or Docker change was made to add this layer.

## Isolation note

Every prior sprint kept `ai/` → `app/` a one-way dependency (`ai/` reads `app/`'s logging/exceptions/config; nothing in `app/` read `ai/`). Sprint 3's objective — "expose the AI Runtime through internal FastAPI endpoints" — cannot be done without crossing that boundary once, from this one package. `app/api/ai/router.py` and `app/main.py` (a two-line addition: import + `include_router`) are the only two files under `app/` that reference `ai/`. Nothing in `ai/` was changed to depend on `app/api/`, and no other file under `app/routes/` or `app/services/` was touched.

## Files

| File | Purpose |
|---|---|
| `router.py` | The `APIRouter` (prefix `/api/v1/ai`) with all six endpoints, each using `Depends(...)` from `ai/dependencies.py` |
| `schemas.py` | Response models (one per endpoint), the two query-parameter validation models, and a note re-exporting `app.schemas.ErrorResponse` as this package's error model |

## Error handling

Every AI exception (`ai/core/exceptions.py`) subclasses `app.core.exceptions.OMSBusinessError`, so the application's existing global exception handler (`register_exception_handlers`, already called once in `app/main.py`) formats every error from this package into the same `{"error", "detail", "request_id"}` shape as the rest of the API, with zero new handler registration. `AIInvalidCapabilityError` (400) and `AIProviderNotFoundError` (404, from Sprint 2) are the two exceptions this package's routes can actually raise; FastAPI's own `Query(min_length=1)` validation produces the 422s for blank query values.

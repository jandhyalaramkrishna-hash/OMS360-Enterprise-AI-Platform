# AI Provider Framework — `ai/providers/`

**Status (Sprint 4, 2026-07-19+): the Provider Framework now has a provider whose `complete()` actually runs — `MockAIProvider` — plus a `ProviderFactory` for construction and a `ProviderHealthChecker` for live (but safe) probing. Still isolated: no route in `app/main.py` was added or changed this sprint, and no real vendor (OpenAI, Claude/Anthropic, Gemini, Azure OpenAI) was implemented.**

This file documents the provider layer specifically, per `docs/governance/DEVELOPMENT-STANDARDS.md` §8 ("module-level READMEs live beside the module they document"). See `ai/README.md` for the AI Service Layer as a whole.

## Purpose

Every AI capability in this project — starting with the documented AI Customer Support Chatbot and, as of Sprint 4, the in-process `AIChatService` — needs a uniform way to call *some* completion-generating backend without hardcoding which one. This package is that seam: one abstract interface (`BaseProvider`), a registry of named instances (`ProviderRegistry`), a factory that knows how to construct them (`ProviderFactory`), and a way to check whether a given provider is actually alive (`ProviderHealthChecker`) — all independent of which concrete provider is selected at runtime.

## Components

| File | Sprint | Purpose |
|---|---|---|
| `base.py` | 2 | `BaseProvider` — abstract interface every provider implements: `is_configured() -> bool`, `async complete(prompt, **kwargs) -> dict`. |
| `registry.py` | 2 | `ProviderRegistry` — register/look-up/list provider instances by name. |
| `openai_provider.py`, `anthropic_provider.py`, `azure_openai_provider.py`, `ollama_provider.py` | 2 | Four **prepared-but-never-called** adapters. Each correctly reports `is_configured()` from its own environment variables, but `complete()` deliberately raises `AIProviderNotConfiguredError` rather than making any network/SDK call. No LLM SDK dependency has been added to `requirements.txt` for any of them. |
| `mock_provider.py` | **4** | `MockAIProvider` — the **first provider whose `complete()` actually returns a result**. Fully in-process, deterministic, no network call, no credential. Always reports itself configured by default (`always_configured=True`). Constructible with `simulate_failure=True` (raises `AIProviderCallFailedError`) or `simulated_latency_ms=<n>` for exercising error-handling and latency-recording paths in tests. |
| `factory.py` | **4** | `ProviderFactory` — owns the name → class mapping for all five known providers. `create(name)`, `create_all()`, `build_registry()`. Replaces the Sprint 2 hardcoded provider-class tuple that used to live inside `ai.services.factory.ServiceFactory`. |
| `health.py` | **4** | `ProviderHealthChecker` — a **live** health probe: calls `provider.complete()` with a fixed probe prompt and reports whether it succeeded. Distinct from `ai.services.health_service.AIHealthService`, which only inspects configuration and never calls a provider. Safe for every provider in this package, since the four prepared adapters still guarantee `complete()` never reaches the network, and `MockAIProvider` never leaves the process either. |

## Configuration-based provider selection

The *active* provider is selected purely through configuration, never hardcoded:

1. `AI_ENABLED` (env var, read by `ai.runtime.config.RuntimeConfiguration`) is the master kill switch. Nothing runs — including `MockAIProvider` — unless this is `true`.
2. `AI_PROVIDER_NAME` (or its fallback, `AI_PROVIDER`) selects which registered provider name to use — e.g. `AI_PROVIDER_NAME=mock`.
3. `AI_API_KEY` is required for every provider **except** `mock`, which needs no credential by design (`ai.runtime.validation` special-cases it — see `_NO_API_KEY_REQUIRED_PROVIDERS`).
4. `AIService.get_selected_provider()` / `AIChatService._resolve_provider()` resolve `AI_PROVIDER_NAME` against the shared `ProviderRegistry` — the same registry both `AIService`/`AIHealthService` (Sprint 2) and `AIChatService` (Sprint 4) use, built via `ProviderFactory.build_registry()`.
5. Any caller can also override the configured default per-call with an explicit `provider_name=` argument (`AIChatService.send_message(message, provider_name="mock")`).

A minimal working configuration for local testing, requiring **no external credentials**:

```
AI_ENABLED=true
AI_PROVIDER_NAME=mock
```

## AI Chat Service (`ai/services/chat_service.py`)

`AIChatService.send_message(message, provider_name=None)` is the first call chain in this project that reaches a provider's `complete()` and returns a real (simulated) result. It composes:

- `AIService` — the `AI_ENABLED` gate and configuration-based provider selection (unchanged from Sprint 2).
- `ProviderRegistry` — explicit `provider_name=` override.
- `ProviderHealthChecker` — `AIChatService.health_check()` / `health_check_all()`.
- `AIMetrics` (Sprint 2, unchanged) — every `send_message()` call increments `request_count`/`response_count`/`error_count` and records provider latency, so `GET /api/v1/ai/metrics` (Sprint 3, once a route is wired to this service) reflects real chat activity for the first time.

Errors are all existing/`AIServiceError`-derived types with consistent JSON responses once wired into a route: `AIChatInvalidRequestError` (422, blank message), `AIFeatureDisabledError` (403, `AI_ENABLED=false`), `AIProviderNotConfiguredError` (503, no/unusable provider), `AIProviderNotFoundError` (404, unknown explicit `provider_name=`), `AIProviderCallFailedError` (502, provider raised during the call — e.g. `MockAIProvider(simulate_failure=True)`).

## What Sprint 4 explicitly does NOT do

Per the Sprint 4 brief: no real vendor implementation (OpenAI, Claude/Anthropic, Gemini, Azure OpenAI — the four existing adapters remain exactly as prepared-but-never-called as they were in Sprint 2), no RAG, no MCP, no AI Agents, no Kafka integration, no database integration, and no new FastAPI route was added to `app/main.py` or `app/api/ai/`. `AIChatService` and `ProviderHealthChecker` are built, unit-tested, and reachable via `ai.dependencies.get_chat_service()` / `get_provider_health_checker()`, but nothing in `app/` calls them yet — wiring a chat endpoint is a candidate for a future, separate, explicitly-approved sprint (see `docs/release/SPRINT-LOG.md`).

## Tests

`tests/ai/test_mock_provider.py`, `tests/ai/test_provider_factory.py`, `tests/ai/test_provider_health.py`, `tests/ai/test_chat_service.py`, `tests/ai/test_dependencies_sprint4.py`, plus additive changes to `tests/ai/test_service_factory.py` (provider count 4 → 5) and `tests/ai/test_runtime_validation.py` (mock's API-key exemption). Same conventions as every other `ai/` test: plain `def test_...()` functions calling `asyncio.run(...)` rather than `async def`, so no `pytest-asyncio` dependency is needed; `monkeypatch` for anything environment-dependent.

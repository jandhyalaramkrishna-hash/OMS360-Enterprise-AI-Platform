# Enterprise Integration / Unified AI Workflow — `ai/integration/`

**Status (Sprint 9, 2026-07-20 IST+, Final Release v1.0.0): the integration package composes the five AI modules built across Sprints 1–8 — Provider Framework, RAG, MCP, Multi-Agent, and AI Evaluation — into a single end-to-end call chain (`AIWorkflowService`) and a single unified health report (`PlatformHealthChecker`). No new retrieval, tool-call, agent-run, evaluation, or provider-call logic was added — every step is a direct call into that module's own existing, unmodified service.**

This file documents the integration package specifically, per `docs/governance/DEVELOPMENT-STANDARDS.md` §8 ("module-level READMEs live beside the module they document"). See `ai/README.md` for the AI Service Layer as a whole.

## Purpose

Sprints 1–8 each built one AI capability in isolation, deliberately never reaching across module boundaries except through `ai/dependencies.py`'s shared singletons. Sprint 9's brief ("Enterprise Integration") asks for the opposite: prove those pieces actually work together, without rebuilding or duplicating any of them. This package is that proof, expressed as code: `AIWorkflowService` chains RAG → MCP → Agents → Provider (chat) → Evaluation into one call, and `PlatformHealthChecker` aggregates every module's own existing health checker into one report.

## Components

| File | Sprint | Purpose |
|---|---|---|
| `workflow_service.py` | **9** | `AIWorkflowService.run(order_id, query=None) -> WorkflowResult` — the Unified AI Workflow: `RAGSearchService.search()` → `MCPServer.call_tool("order_lookup", ...)` → `AgentService.run()` (all six mock agents, in lifecycle order) → `AIChatService.send_message()` (seeded with the retrieved RAG context) → `EvaluationService.evaluate()` (the built-in `MockEvalDataset`, scored through the same chat call path step 4 used). |
| `health.py` | **9** | `PlatformHealthChecker.check() -> PlatformHealthReport` — aggregates `AIHealthService` (Sprint 2, config-only), `ProviderHealthChecker` (Sprint 4, live), `MCPHealthChecker` (Sprint 6, live), `AgentHealthChecker` (Sprint 7, live), and an `AIMetrics` snapshot (Sprint 2) into one report. Performs no capability gating of its own — reachable and meaningful even when a feature flag is off, mirroring `AIHealthService`'s own philosophy. |

One small additive change was made to an existing Sprint 1/7 file to support this: `AgentOrchestrator` gained a `get_agent(name)` passthrough method (mirroring `MCPToolRegistry.get_tool()`), so `PlatformHealthChecker` can fetch actual agent objects for its live probes — see `ai/agents/orchestrator.py`.

## The workflow, end to end

`ai/dependencies.py` assembles both Sprint 9 collaborators once, at module import time, from the **same** singletons Sprints 2–8 already built — no second `AIService`, `ProviderRegistry`, `MCPToolRegistry`, `AgentOrchestrator`, `EvalRunner`, or `MockAIProvider` instance is constructed anywhere in this package:

1. `AIWorkflowService` is built from `_ai_service`, `_search_service`, `_mcp_server`, `_agent_service`, `_chat_service`, `_evaluation_service`, `_mock_eval_dataset` — all already-existing Sprint 2–8 singletons.
2. `PlatformHealthChecker` is built from `_ai_health_service`, `_provider_health_checker`/`_provider_registry`, `_mcp_health_checker`/`_tool_registry`, `_agent_health_checker`/`_agent_orchestrator`, and the shared `AIMetrics` singleton — likewise all already-existing.

`AIWorkflowService.run(order_id, query)` is the call that exercises all five modules together — reachable via `ai.dependencies.get_ai_workflow_service()` and direct unit/integration tests this sprint, **not** from any HTTP route (see "What Sprint 9 explicitly does NOT do" below). A typical run:

```python
workflow = get_ai_workflow_service()
result = await workflow.run(order_id="ORD-1001", query="what is your refund policy?")

result.rag_result.context.text            # retrieved FAQ context
result.mcp_result.output                  # mock order snapshot (status, items, total)
result.agent_history                      # ["order_agent", "inventory_agent", ...]
result.chat_result.content                # "[mock] ..." completion, seeded with RAG context
result.evaluation_summary.accuracy.accuracy  # 1.0 - the built-in mock dataset always passes
```

`PlatformHealthChecker.check()` is reachable via `ai.dependencies.get_platform_health_checker()` **and** as the one HTTP route this sprint adds, `GET /api/v1/ai/platform/health` (see `app/api/ai/router.py`):

```python
report = await get_platform_health_checker().check()
report.overall_healthy       # True iff runtime config has no errors AND every MCP tool AND every agent is healthy
report.provider_results      # per-provider ProviderHealthResult, informational, does not gate overall_healthy
```

## Design decisions (DEC-0022)

1. **No new registry, no new enablement mechanism.** Every collaborator `AIWorkflowService`/`PlatformHealthChecker` is built from is a singleton Sprints 2–8 already constructed in `ai/dependencies.py`. This sprint adds zero new `require_capability(...)` calls of its own — each step's own existing gate (`rag_enabled`/`mcp_enabled`/`agents_enabled`/`evals_enabled`, or the master `ai_enabled` check inside `AIChatService.send_message`) applies exactly as it already did standalone. A capability being off fails the workflow at exactly the step that needs it, the same fail-closed behavior every module already had.
2. **The evaluation step exercises the SAME chat call path the workflow's own chat step used**, not a second, disconnected mock completion mechanism — `AIWorkflowService._chat_target` is a thin passthrough to the same `AIChatService.send_message()` call used for step 4, so evaluating "how well did the platform's chat capability perform" is genuinely evaluating this run, not an unrelated side-check.
3. **The health endpoint is intentionally NOT capability-gated.** A health report needs to explain *why* something is unhealthy or disabled, so it must stay reachable even when the very capability it reports on is off — the same design `AIHealthService` (Sprint 2) already established. `overall_healthy` is defined narrowly (runtime config validity + every MCP tool + every agent's live probe) and deliberately excludes provider reachability from gating it, since most providers are expected to be unconfigured — this mirrors `AIHealthService`'s own "healthy = no configuration errors" definition rather than "everything is configured and reachable."
4. **Only the explicitly-requested endpoint was wired into `app/`.** Sprint 9's brief asks for "a unified health/status endpoint for all AI modules" by name; it does not ask for the workflow itself to be HTTP-reachable. Consistent with every prior sprint's scope discipline (Sprint 3 wired exactly what its brief asked for and nothing more), `GET /api/v1/ai/platform/health` was added to `app/api/ai/router.py`, while `AIWorkflowService` remains reachable only via dependency injection and tests — matching how `AgentService`, `EvaluationService`, `RAGSearchService`, and `MCPServer` were each left HTTP-unreachable in their own introducing sprint.
5. **One small additive method, not a workaround.** `AgentOrchestrator.get_agent(name)` was added (mirrors `MCPToolRegistry.get_tool()`) rather than giving `PlatformHealthChecker` a second, independent reference to the agent registry — the orchestrator remains the single place that answers both "which agents exist" and "give me one of them," consistent with the "one shared collaborator" pattern established since DEC-0017.

## What Sprint 9 explicitly does NOT do

No real vendor provider, no real vector database, no real MCP client/transport, no real AI model, no real LLM evaluation service, no Kafka integration, no database integration, and no external API call were added — every step this package chains together was already a Sprint 1–8 mock, and remains one. No new technology or external service was introduced. No existing module was rebuilt, duplicated, or redesigned — `ai/integration/` contains orchestration code only, composing collaborators it does not own. `AIWorkflowService` itself is not wired into any HTTP route this sprint (see design decision 4 above).

## Tests

- `tests/ai/test_workflow_service.py` — `AIWorkflowService`, built with isolated, locally-constructed collaborators (happy path, blank/invalid `order_id`, each capability's disabled path propagating from its own step).
- `tests/ai/test_platform_health.py` — `PlatformHealthChecker`, built with isolated, locally-constructed collaborators (healthy path, a simulated configuration error, metrics snapshot inclusion).
- `tests/ai/test_orchestrator_get_agent_sprint9.py` — the additive `AgentOrchestrator.get_agent()` method.
- `tests/ai/test_dependencies_sprint9.py` — the assembled Sprint 9 singletons, and that both share the same Sprint 2–8 collaborators rather than constructing second instances of anything.
- `tests/api/ai/test_platform_health_route.py` — `GET /api/v1/ai/platform/health` against the real Sprint 1–9 singletons: response shape, every tool/agent reported, reachable regardless of `AI_ENABLED`, present in the OpenAPI schema.
- `tests/integration/test_ai_workflow_end_to_end.py` — the full production-shaped assembly (every real provider, all 4 real MCP tools, all 6 real mock agents, the real built-in RAG documents and eval dataset) exercised end to end, including a metrics-snapshot assertion and a cross-check that `AIWorkflowService` and `PlatformHealthChecker` agree on which tools/agents exist.

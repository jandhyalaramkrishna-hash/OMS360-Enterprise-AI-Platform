# MCP Foundation — `ai/mcp/`

**Status (Sprint 6, 2026-07-20+): the MCP package now has a full, real (mock) tool-calling pipeline — `MCPToolFactory` → `MCPToolRegistry` (Sprint 1, reused) → `MCPRequestRouter` → `MCPServer` — the first component in this project that actually dispatches a tool call end to end. Four deterministic mock tools (`order_lookup`, `inventory_lookup`, `delivery_status_lookup`, `kitchen_status_lookup`) are registered and callable. No real MCP client, transport, or external service was added.**

This file documents the MCP package specifically, per `docs/governance/DEVELOPMENT-STANDARDS.md` §8 ("module-level READMEs live beside the module they document"). See `ai/README.md` for the AI Service Layer as a whole.

## Purpose

The Model Context Protocol is, at its core, a way for a model-facing caller to discover a set of callable tools and invoke one by name with arguments. This package builds that shape entirely in-process: a registry of tools, a router that dispatches `"tools/list"`/`"tools/call"`-style requests to them, and a server that gates access and offers a plain async API over the router. Sprint 6's explicit goal is the *architecture*, not a real integration — every concrete tool shipped this sprint is a mock, run entirely in-process, and no real MCP client or wire transport exists yet.

## Components

| File | Sprint | Purpose |
|---|---|---|
| `base.py` | 1 | `MCPTool` — abstract interface every tool implements: `name`, `description`, `input_schema` (JSON Schema dict), `async execute(**kwargs) -> dict`. Unchanged this sprint. |
| `registry.py` | 1 | `MCPToolRegistry` — register/look-up/list tool instances by name. Unchanged this sprint; Sprint 6 registers new tools into the *same* shared singleton rather than building a second registry (see "Design" below). |
| `models.py` | **6** | `MCPRequest`/`MCPResponse` (a JSON-RPC-style `method`+`params` envelope and its response, mirroring the real protocol's shape without any wire format), `ToolDescriptor` (one entry per tool for `tools/list`), `ToolCallResult` (the outcome of a `tools/call`). |
| `router.py` | **6** | `MCPRequestRouter.route(request) -> MCPResponse` — method dispatch (`"tools/list"`, `"tools/call"`) plus protocol-level request validation (unknown method, missing tool name, missing required argument per the tool's own `input_schema`). Enforces `MCPConfig.tool_call_timeout_ms` around every `tool.execute()` call via `asyncio.wait_for`. Does not decide whether MCP is enabled — that's `MCPServer`'s job, before a request ever reaches the router. |
| `server.py` | **6** | `MCPServer(router, ai_service)` — the ergonomic entry point: `async list_tools()` / `async call_tool(name, arguments)`, each gated on `AIService.require_capability("mcp_enabled")` before delegating to the router. |
| `health.py` | **6** | `MCPHealthChecker` — a **live** probe, mirroring `ai.providers.health.ProviderHealthChecker`'s role for the provider framework: actually calls each tool's `execute()` (with generic placeholder arguments built from the tool's own `input_schema`) rather than only inspecting configuration. Safe for every tool in this package, since all four are deterministic in-process mocks. |
| `config.py` | **6** | `MCPConfig`/`load_mcp_config()` — **tuning only** (`tool_call_timeout_ms`, default 5000), read from `MCP_TOOL_CALL_TIMEOUT_MS`. Self-contained — does not import `ai/runtime/config.py` or `ai/config.py`. See "Configuration" below. |
| `tools/order_lookup_tool.py` | **6** | `OrderLookupTool` — given `order_id`, returns a deterministic mock order snapshot (status, items, total). |
| `tools/inventory_lookup_tool.py` | **6** | `InventoryLookupTool` — given `item_id`, returns a deterministic mock stock snapshot (quantity, in-stock, reorder flag). |
| `tools/delivery_status_tool.py` | **6** | `DeliveryStatusTool` — given `delivery_id`, returns a deterministic mock delivery snapshot (status, driver, ETA). |
| `tools/kitchen_status_tool.py` | **6** | `KitchenStatusTool` — given `kitchen_id`, returns a deterministic mock kitchen-load snapshot (status, active orders, avg prep time). |
| `tools/_deterministic.py` | **6** | `pick()`/`pick_int()` — a fixed function of the input id string (a character-sum checksum), **not** `random` — same id always yields the same mock output, across every run and process. |
| `tools/factory.py` | **6** | `MCPToolFactory.create_all()`/`known_tool_names()` — owns construction of all four known mock tools, mirroring `ai.providers.factory.ProviderFactory`'s role for the provider framework. |

## Configuration — tuning vs. enablement, deliberately separate (same split as RAG, DEC-0018)

1. **Enablement** — is MCP allowed to run at all? Reuses the *existing* Sprint 2 mechanism unchanged: `MCP_ENABLED` + the master `AI_ENABLED` env vars, read by `ai.runtime.config.RuntimeConfiguration`, checked via `AIService.require_capability("mcp_enabled")` — the same guard Sprint 5's `RAGSearchService` reuses for `rag_enabled`. `MCPServer.list_tools()`/`call_tool()` call it on every request; nothing in `ai/runtime/`, `ai/config.py`, or `ai/services/ai_service.py` was modified this sprint.
2. **Tuning** — given that MCP is enabled, how long a single tool call is allowed to run. `MCP_TOOL_CALL_TIMEOUT_MS` (default 5000) is never a fail-closed gate — an unset or invalid value always falls back to the default, it never disables MCP. `MCPRequestRouter` enforces it around every tool call, so even today's instant, in-process mock tools are bounded the same way a future real (I/O-bound) tool would need to be.

A minimal working configuration for local testing, requiring **no external credentials**:

```
AI_ENABLED=true
MCP_ENABLED=true
```

(`MCP_TOOL_CALL_TIMEOUT_MS` is optional — it has a working default.)

## The pipeline, end to end

`ai/dependencies.py` assembles the pipeline once, at module import time, as process-lifetime singletons — the same pattern used for Sprint 4's provider framework and Sprint 5's RAG pipeline:

1. `MCPToolFactory.create_all()` → four tool instances
2. Each is registered into the **same** `_tool_registry` singleton Sprint 1 already built (not a second registry)
3. `MCPRequestRouter(_tool_registry, mcp_config)` is constructed over it
4. `MCPServer(router, ai_service)` composes the router with the *existing* Sprint 2 `AIService` singleton (reused, not duplicated)

`MCPServer.list_tools()` / `MCPServer.call_tool(name, arguments)` are the calls that exercise all of this together — reachable via `ai.dependencies.get_mcp_server()`, not yet from any HTTP route (see below).

Errors are all `AIServiceError`-derived types with consistent JSON responses once wired into a route: `AIMCPInvalidRequestError` (422, blank tool name or a missing required argument), `AIToolNotFoundError` (404, reused from Sprint 1 — an unregistered tool name), `AIMCPUnsupportedMethodError` (400, an unrecognized `method` on a raw `MCPRequest`), `AIMCPToolExecutionError` (502, the tool raised during `execute()`), `AIMCPToolCallTimeoutError` (504, the tool exceeded `tool_call_timeout_ms`), `AIFeatureDisabledError` (403, `AI_ENABLED` or `MCP_ENABLED` false).

## Design decisions (DEC-0019)

- **One shared tool registry, not a second one.** The four Sprint 6 mock tools are registered into the exact `MCPToolRegistry` singleton Sprint 1 already created and exposed via `ai.dependencies.get_tool_registry()`, the same "reuse the existing shared collaborator" choice Sprint 4 made for `ProviderRegistry` (DEC-0017). Any future consumer of `get_tool_registry()` — including eventual Agents work — sees the same tools `MCPServer` does.
- **Router vs. Server split.** `MCPRequestRouter` owns protocol-shape dispatch and validation (method routing, missing-name/argument checks) and is usable on its own with a raw `MCPRequest`/`MCPResponse` envelope — useful if a future real MCP transport needs to drive it directly. `MCPServer` owns the *policy* concern (capability gating) and the *ergonomics* concern (plain async methods instead of building envelopes by hand). Neither layer duplicates the other's responsibility.
- **Generic, schema-driven request/health validation.** Both the router's required-argument check and the health checker's probe-argument construction read each tool's own `input_schema` rather than hardcoding per-tool argument names — adding a fifth tool later requires no change to either.

## What Sprint 6 explicitly does NOT do

Per the Sprint 6 brief: no real MCP client, no real vendor implementation (OpenAI, Claude/Anthropic, Gemini), no RAG integration, no AI Agents, no Kafka integration, no database integration, no external API call, and no new FastAPI route was added to `app/main.py` or `app/api/ai/`. Every concrete tool (`OrderLookupTool`, `InventoryLookupTool`, `DeliveryStatusTool`, `KitchenStatusTool`) returns mock data derived only from its input id — nothing here reads `app/services/order_service.py`, `inventory_service.py`, `delivery_service.py`, or `kitchen_service.py`. `MCPServer` is built, unit-tested, and reachable via `ai.dependencies.get_mcp_server()`, but nothing in `app/` calls it yet — wiring a tool-listing/tool-call endpoint is a candidate for a future, separate, explicitly-approved sprint (see `docs/release/SPRINT-LOG.md`).

## Tests

`tests/ai/test_mcp.py` (Sprint 1, `MCPToolRegistry` — unchanged, still passing), plus new Sprint 6 files: `tests/ai/test_mcp_tools.py`, `test_mcp_tool_factory.py`, `test_mcp_router.py`, `test_mcp_server.py`, `test_mcp_health.py`, `test_mcp_config.py`, `test_dependencies_sprint6.py`. Same conventions as every other `ai/` test: plain `def test_...()` functions calling `asyncio.run(...)` rather than `async def`, so no `pytest-asyncio` dependency is needed; `monkeypatch` for anything environment-dependent.

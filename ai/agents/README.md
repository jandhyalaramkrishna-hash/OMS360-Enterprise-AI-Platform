# Multi-Agent Foundation — `ai/agents/`

**Status (Sprint 7, 2026-07-20 IST+): the agents package now has a full, real (mock) multi-agent pipeline — `AgentFactory` → `AgentRegistry` (composed by `AgentOrchestrator`, Sprint 1 reused) → `AgentOrchestrator` → `AgentService` — the first component in this project that actually chains multiple agents and exchanges mock messages between them end to end. Six deterministic mock agents (Order, Inventory, Kitchen, Delivery, Customer Support, Analytics) are registered and runnable in sequence. No real AI model, Kafka, or database was added.**

This file documents the agents package specifically, per `docs/governance/DEVELOPMENT-STANDARDS.md` §8 ("module-level READMEs live beside the module they document"). See `ai/README.md` for the AI Service Layer as a whole.

## Purpose

A multi-agent system is, at its core, a set of independently-runnable units (agents) that each contribute to a shared piece of state and can signal one another. This package builds that shape entirely in-process: a registry of agents, an orchestrator that runs a named sequence of them against a shared `AgentContext`, and a mock message bus agents use to communicate. Sprint 7's explicit goal is the *architecture*, not a real integration — every concrete agent shipped this sprint is a mock, run entirely in-process, and no real AI model drives any agent's decision-making yet.

## Components

| File | Sprint | Purpose |
|---|---|---|
| `base.py` | 1 / **7** | `AgentBase` — abstract interface every agent implements: `name`, `async run(context) -> context`. `AgentContext` — shared state (`input`, `data`, `history`); Sprint 7 adds a `messages` field (default `[]`) for the mock message log. |
| `registry.py` | **7** | `AgentRegistry` — register/look-up/list agent instances by name, extracted from `AgentOrchestrator`'s previously-internal dict (see "Design" below). |
| `orchestrator.py` | 1 / 7 / **9** | `AgentOrchestrator.run_sequence(agent_names, context)` — runs a named list of registered agents in order, each receiving the context the previous one produced. Sprint 7: now composes an `AgentRegistry` instead of its own dict, and wraps an agent's unexpected exception as `AIAgentExecutionError` rather than letting it propagate unclassified. Fully backward compatible — `tests/ai/test_agents.py` (Sprint 1) passes unmodified. Sprint 9 adds one further additive method, `get_agent(name)` — a plain passthrough to the registry (mirrors `MCPToolRegistry.get_tool()`), added so `ai.integration.health.PlatformHealthChecker` can fetch actual agent objects for its live probes without a second reference to the registry. |
| `messaging.py` | **7** | `AgentMessage` / `AgentMessageBus` — a mock, in-process, synchronous message bus. `publish()` appends an `AgentMessage` to `context.messages`; there is no real transport of any kind. |
| `health.py` | **7** | `AgentHealthChecker` — a **live** probe, mirroring `ai.mcp.health.MCPHealthChecker`'s role for the MCP framework: actually calls each agent's `run()` with a harmless probe context. |
| `agent_service.py` | **7** | `AgentService(orchestrator, ai_service)` — the ergonomic, policy-enforcing entry point: `async run(agent_names, context)` / `list_agents()`, each gated on `AIService.require_capability("agents_enabled")` before delegating to the orchestrator. |
| `factory.py` | **7** | `AgentFactory.create_all()` / `known_agent_names()` — owns construction of all six known mock agents, injecting the shared `AgentMessageBus` into each. |
| `mock_agents/order_agent.py` | **7** | `OrderAgent` — deterministic mock order status; publishes `order_received_for_prep` to `kitchen_agent`. |
| `mock_agents/inventory_agent.py` | **7** | `InventoryAgent` — deterministic mock stock check; publishes `stock_check_complete` to `order_agent`. |
| `mock_agents/kitchen_agent.py` | **7** | `KitchenAgent` — deterministic mock prep time; publishes `order_ready_for_pickup` to `delivery_agent`. |
| `mock_agents/delivery_agent.py` | **7** | `DeliveryAgent` — deterministic mock driver assignment + ETA; publishes `delivery_dispatched` to `customer_support_agent`. |
| `mock_agents/customer_support_agent.py` | **7** | `CustomerSupportAgent` — reads messages addressed to it and summarizes the latest update for the customer. |
| `mock_agents/analytics_agent.py` | **7** | `AnalyticsAgent` — terminal agent; summarizes how many agents ran and how many messages were exchanged. |

All six mock agents reuse `ai.mcp.tools._deterministic.pick()`/`pick_int()` (Sprint 6) rather than duplicating a second checksum-based mock-data helper — same deterministic-per-id guarantee, one implementation.

## The pipeline, end to end

`ai/dependencies.py` assembles the pipeline once, at module import time, as process-lifetime singletons — the same pattern used for Sprint 5's RAG pipeline and Sprint 6's MCP pipeline:

1. `AgentFactory(message_bus).create_all()` → six agent instances, each holding the same shared `AgentMessageBus`
2. Each is registered into the **same** `_agent_orchestrator` singleton Sprint 1 already built (not a second orchestrator)
3. `AgentService(orchestrator, ai_service)` composes the orchestrator with the *existing* Sprint 2 `AIService` singleton (reused, not duplicated)

`AgentService.run(agent_names, context)` is the call that exercises all of this together — reachable via `ai.dependencies.get_agent_service()`, not yet from any HTTP route (see below). A typical full-lifecycle run:

```python
context = AgentContext(input="ORD-123", data={"order_id": "ORD-123"})
context = await agent_service.run(
    ["order_agent", "inventory_agent", "kitchen_agent", "delivery_agent",
     "customer_support_agent", "analytics_agent"],
    context,
)
```

Errors are all `AIServiceError`-derived types with consistent JSON responses once wired into a route: `AIAgentNotRegisteredError` (404, reused from Sprint 1 — an unknown agent name), `AIAgentExecutionError` (502, an agent raised during `run()`), `AIFeatureDisabledError` (403, `AI_ENABLED` or `AGENTS_ENABLED` false).

## Design decisions (DEC-0020)

- **One shared agent orchestrator, not a second one.** The six Sprint 7 mock agents are registered into the exact `AgentOrchestrator` singleton Sprint 1 already created and exposed via `ai.dependencies.get_agent_orchestrator()`, the same "reuse the existing shared collaborator" choice DEC-0017/0018/0019 made for their respective registries.
- **Registry extracted from the orchestrator, not duplicated beside it.** `AgentOrchestrator`'s Sprint 1 `_agents` dict became a proper `AgentRegistry` class (mirroring `MCPToolRegistry`/`ProviderRegistry`) that the orchestrator now composes — a behavior-preserving refactor, not a second, parallel registry. `AgentOrchestrator()` with no constructor argument still creates its own registry automatically, so Sprint 1's tests needed zero changes.
- **Orchestrator vs. Service split.** `AgentOrchestrator` owns pure execution mechanics (register/list/run a sequence) and has no knowledge of enablement — mirroring `MCPRequestRouter`'s role from Sprint 6. `AgentService` owns the *policy* concern (capability gating). Neither layer duplicates the other's responsibility.
- **Mock messaging lives on the context, not a separate transport.** `AgentMessageBus.publish()` appends directly to `AgentContext.messages` rather than any external queue — per the brief's explicit "mock messages only" requirement, there is nothing here that could accidentally be mistaken for a Kafka producer.

## What Sprint 7 explicitly does NOT do

Per the Sprint 7 brief: no OpenAI, Claude API, Gemini, or any real AI model driving an agent's decisions; no Kafka integration; no database integration; no external API call; and no new FastAPI route was added to `app/main.py` or `app/api/ai/`. Every concrete agent (`OrderAgent`, `InventoryAgent`, `KitchenAgent`, `DeliveryAgent`, `CustomerSupportAgent`, `AnalyticsAgent`) returns mock data derived only from its input id — nothing here reads `app/services/order_service.py`, `inventory_service.py`, `delivery_service.py`, or `kitchen_service.py`. `AgentService` is built, unit-tested, and reachable via `ai.dependencies.get_agent_service()`, but nothing in `app/` calls it yet — wiring an agent-run endpoint is a candidate for a future, separate, explicitly-approved sprint (see `docs/release/SPRINT-LOG.md`).

## Tests

`tests/ai/test_agents.py` (Sprint 1, `AgentOrchestrator` — unchanged, still passing), plus new Sprint 7 files: `tests/ai/test_agent_registry.py`, `test_agent_messaging.py`, `test_agent_health.py`, `test_agent_factory.py`, `test_mock_agents.py`, `test_agent_orchestrator_sprint7.py`, `test_agent_service.py`, `test_dependencies_sprint7.py`. Same conventions as every other `ai/` test: plain `def test_...()` functions calling `asyncio.run(...)` rather than `async def`, so no `pytest-asyncio` dependency is needed.

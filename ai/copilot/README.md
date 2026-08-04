# AI Copilot

**"AI Copilot Sprint 1" — Phase 1**: AI Copilot menu, AI Chat interface, Business Question & Answer, Executive Summary, Business Insights.

**"AI Copilot Sprint 2"**: AI SQL Assistant (LLM-enhanced Explain SQL), AI Root Cause Analysis, AI QA Assistant, AI Documentation Assistant, AI Learning Assistant. Same Hybrid architecture, same shared `AIProviderManager`/`ProviderRegistry` singletons, same "reword/elaborate, never invent" discipline as Sprint 1 — see each module's own docstring below for exactly what is real-data-grounded vs. LLM-optional in it.

Tracked from `DEC-0033` onward in `docs/governance/DECISION-LOG.md`. This is a fresh line, not a continuation of the closed Sprint 1-9 AI Runtime (see `DEC-0022`), which is untouched by everything in this package.

## Architecture (Hybrid, per explicit Product Owner instruction)

Business facts — pending orders, failed orders, inventory, kitchen, delivery, sales, monitoring — are **always** answered from the real OMS-360 MySQL database via deterministic intent matching and direct, parameterized SQLAlchemy queries. They are never fabricated and never routed through an LLM to be computed.

An LLM, if one is configured, is used **only** for reasoning and language tasks layered on top of that same real data — rephrasing an already-computed sentence today, and (in later phases) Explain SQL, Root Cause Analysis, QA test generation, documentation, interview coaching, and similar. It is never allowed to generate or alter a business number: `BusinessQAService._numbers_preserved()` verifies every digit sequence in the original deterministic sentence still appears in a reworded one, and discards the rewording otherwise.

If no LLM provider is configured, Business Q&A, Executive Summary, and Business Insights all still work completely via the deterministic engine alone — this is not a degraded mode, it is the default mode.

### AI Provider Manager (AUTO chain)

`provider_manager.AIProviderManager` selects a real, configured LLM provider automatically:

```
AUTO -> OpenAI configured?      -> use OpenAI
     -> else Anthropic configured? -> use Anthropic
     -> else Ollama configured?    -> use Ollama
     -> else Azure OpenAI configured? -> use Azure OpenAI
     -> else                       -> deterministic-only (no LLM)
```

`AI_COPILOT_PROVIDER` (env var) pins one provider explicitly, overriding AUTO; falls back to AUTO if the pinned provider isn't actually configured. The `mock` provider is deliberately excluded from the AUTO chain — it only echoes input text and cannot perform real reasoning, so treating it as "configured" would be misleading.

This reuses the same `ProviderRegistry` singleton (`ai/providers/registry.py`) every other AI Runtime component already shares — "one shared collaborator," consistent with `DEC-0017` through `DEC-0022` — not a second, copilot-only registry.

## Modules

| File | Responsibility |
|---|---|
| `provider_manager.py` | `AIProviderManager` — AUTO-selects a real LLM provider, or honestly reports none configured. |
| `intents.py` | `BUSINESS_INTENTS` — one entry per supported business question: trigger phrases, a real SQLAlchemy query handler, and pre-written SQL/related-tables/business-flow display text. `classify_question()` is a plain, explainable keyword matcher — no LLM involved. |
| `business_qa_service.py` | `BusinessQAService.ask()` — the entry point behind `POST /api/v1/ai/copilot/ask`. Matches a question, runs the real query, optionally rewords via the active LLM (guardrailed). SQL/Explain/Related Tables/Business Flow are never included automatically — fetched lazily via `get_sql()`/`get_explanation()`/`get_related_tables()`/`get_business_flow()`, keyed by the `intent` the `ask()` response returned. |
| `executive_summary_service.py` | `ExecutiveSummaryService.build()` — composes a short paragraph from `app.routes.dashboard`'s existing `kpi_bar()`/`analytics_summary()` functions, called directly rather than duplicated. Never LLM-generated. |
| `business_insights_service.py` | `BusinessInsightsService.build()` — a handful of rule-based, explainable-threshold observations over real data (cancellation rate, failed payments, out-of-stock/low-stock, kitchen backlog, pending backlog). |
| `root_cause_service.py` | `RootCauseAnalysisService` — `analyze_failed_orders()`/`analyze_duplicate_orders()`: real, grouped SQL over `failed_orders`/`duplicate_orders` (counts, most-recent examples, and — for duplicates — correlation back to `orders_master`/`failed_orders` by `transaction_id`), plus a natural-language explanation and suggested investigation steps. Deterministic keyword-pattern-matched steps (payment/inventory/timeout/kafka/etc.) by default; an LLM, if configured, may only elaborate on the exact computed counts/reasons it's given — never invent a cause. Zero rows found is a valid, non-error outcome. |
| `qa_assistant_service.py` | `QAAssistantService.generate()` — generates functional/negative/regression/API/SQL-validation test-case text for a real endpoint (`target`), grounded strictly in a caller-supplied `context` string. Deliberately does not introspect the live FastAPI app (avoids fragile coupling) — the caller supplies real facts about the endpoint. Deterministic checklist template by default; an LLM, if configured, writes richer test cases from the same `target`/`context` only. |
| `documentation_assistant_service.py` | `DocumentationAssistantService.generate()` — turns a caller-supplied `facts` block into a structured section (`doc_type`: `readme_section` \| `sprint_summary` \| `release_notes` \| `api_docs`). Never invents a fact not present in `facts` — an LLM, if configured, only organizes/formats/expands the phrasing around them. |
| `learning_assistant_service.py` | `LearningAssistantService` — ships its own small, hand-written, factually-accurate knowledge base (`architecture`, `kafka`, `inventory`, `kitchen`, `delivery`, `monitoring`, `database`), written from reading this repo's own modules. `list_topics()`/`explain_topic()`/`ask()` (simple keyword matching to the nearest topic). An LLM, if configured, may only elaborate/rephrase a topic's real text — never answer from general knowledge about unrelated systems. |

## UI requirement: SQL is never shown automatically

`POST /copilot/ask` returns `answer_text` (and, when matched, `intent`) only — never `sql_text`. A UI shows `[View SQL] [Explain SQL] [Related Tables] [Business Flow]` buttons under a matched answer, and fetches each lazily only if the user clicks it, via the four `GET /copilot/intents/{intent}/...` endpoints. This is enforced by the response schema (`CopilotAskResponse` has no SQL field at all — there is no field to accidentally serialize), not just by application logic choosing not to populate one.

## Enablement

Gated by `RuntimeConfiguration.copilot_enabled` (`COPILOT_ENABLED` env var), which defaults `True` and is checked **independently** of the master `ai_enabled` flag / `is_capability_enabled()`. Every Sprint 1-9 capability flag requires `ai_enabled` (which itself requires a valid provider configuration) to also be true; AI Copilot's core value — Business Q&A against real data — needs no provider at all, so gating it behind `ai_enabled` would make the one AI feature meant to work out of the box invisible by default. See `ai/runtime/config.py`'s `copilot_enabled` field docstring.

## HTTP API

`app/api/ai/copilot_router.py`, prefix `/api/v1/ai/copilot`:

- `POST /ask` — ask a business question.
- `GET /questions` — example supported questions (suggestion chips).
- `GET /intents/{intent}/sql` — View SQL (lazy).
- `GET /intents/{intent}/explain` — Explain SQL (lazy). `?use_ai=true` (default) enriches the deterministic template via a configured LLM, strictly grounded in the intent's own `sql_text`/`related_tables`/`business_flow`; falls back to the deterministic template otherwise.
- `GET /intents/{intent}/related-tables` — Related Tables (lazy).
- `GET /intents/{intent}/business-flow` — Business Flow (lazy).
- `GET /executive-summary` — real-data executive summary paragraph + raw KPIs.
- `GET /business-insights` — rule-based insights list.
- `GET /provider-status` — which real LLM (if any) is currently active.
- `GET /root-cause/failed-orders` — root-cause analysis over the real `failed_orders` table.
- `GET /root-cause/duplicate-orders` — root-cause analysis over the real `duplicate_orders` table.
- `POST /qa-assistant/generate` — generate test cases for a real endpoint (`target`/`context`/`test_types`).
- `POST /docs-assistant/generate` — generate documentation prose from caller-supplied real facts (`doc_type`/`facts`/`title`).
- `GET /learning/topics` — list Learning Assistant knowledge-base topics.
- `GET /learning/topics/{topic}` — explain one topic (`?use_ai=true` default).
- `POST /learning/ask` — ask a free-form question, matched to the nearest topic.

HTML page: `app/static/ai_copilot.html`, served at `/dashboard/ai-copilot` (registered in `app/main.py`, same `Cache-Control: no-store` pattern as the three existing dashboard pages per `DEC-0032`). The nav bar on all three prior dashboard pages was updated symmetrically to link here.

## Testing

- `tests/ai/test_copilot_provider_manager.py` — AUTO chain, explicit override, mock exclusion.
- `tests/ai/test_copilot_intents.py` — catalog integrity, `classify_question()`.
- `tests/ai/test_copilot_business_qa_service.py` — matched/unmatched/invalid questions, the reword guardrail (numbers-preserved acceptance, numbers-changed rejection, provider-failure fallback), lazy detail lookups.
- `tests/ai/test_copilot_business_insights_service.py` — every rule threshold.
- `tests/ai/test_copilot_executive_summary_service.py` — summary composition (monkeypatches `dashboard_routes.kpi_bar`/`analytics_summary` so this module's own formatting logic is what's under test, independent of those functions' own query correctness).
- `tests/ai/test_dependencies_copilot.py` — DI singleton wiring, shared `ProviderRegistry`, `copilot_enabled` independence from `ai_enabled`.
- `tests/ai/test_copilot_root_cause_service.py` — grouped counts/reasons, duplicate-order correlation, AI-elaboration guardrail, empty-data (non-error) path.
- `tests/ai/test_copilot_qa_assistant_service.py` — deterministic checklist template, test_types normalization, AI-generated path, provider-failure fallback.
- `tests/ai/test_copilot_documentation_assistant_service.py` — deterministic template, "never invents facts" check, AI-generated path, provider-failure fallback.
- `tests/ai/test_copilot_learning_assistant_service.py` — knowledge-base topic listing/explaining, `ask()` keyword matching, AI-elaboration guardrail, unknown-topic 404.
- `tests/api/ai/test_copilot_routes.py` — all sixteen HTTP routes end-to-end against an in-memory SQLite database, including the `COPILOT_ENABLED=false` → 403 gate.

`tests/ai/conftest.py`'s `copilot_db` fixture (in-memory SQLite, `StaticPool`) is used by the DB-touching tests above. Business Q&A / Business Insights queries are plain `func.count()`/`filter()` SQLAlchemy — no MySQL-specific SQL — so they run identically against SQLite. `ExecutiveSummaryService` is the one exception: `app/services/kitchen_service.py`'s average-cooking-time query uses MySQL's `TIMESTAMPDIFF`, which SQLite's parser rejects outright — a pre-existing behavior of code this package reuses, not something introduced here (see `docs/governance/DECISION-LOG.md`'s accepted MySQL-only test baseline). `test_copilot_executive_summary_service.py` sidesteps this by testing `ExecutiveSummaryService`'s own composition logic against monkeypatched inputs instead.

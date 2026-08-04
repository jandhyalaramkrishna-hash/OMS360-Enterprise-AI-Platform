# Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform

Enterprise-grade, event-driven food ordering and delivery management system — FastAPI, Apache Kafka, MySQL, Docker — with a complete, mock-based AI Enterprise Platform layered alongside it (Provider Framework, RAG, MCP, Multi-Agent, AI Evaluation, and a unified integration layer). See `PROJECT_CONTEXT.md` for the session-start primer and `docs/governance/MASTER-PROJECT-MEMORY.md` for the full single source of truth.

## Current Status (as of 2026-07-20, IST)

**OMS360 Enterprise AI Platform — v1.0.0 (Final Release). Development on this line is closed.** The AI Enterprise Platform (`ai/`) was built incrementally across nine sprints, each isolated, reviewed, and unit-tested before the next began:

| Sprint | Delivered |
|---|---|
| 1 | AI Service Layer scaffolding (RAG/MCP/Agents/Evals/Prompts primitives), isolated and unwired |
| 2 | AI Runtime Infrastructure — Service Layer, Provider Framework (4 prepared adapters), runtime feature flags, health checks, metrics |
| 3 | AI API Layer — six read-only introspection endpoints wired into `app/main.py` |
| 4 | AI Provider Framework — `MockAIProvider` (the first provider that actually runs), `ProviderFactory`, `AIChatService`, provider health checks |
| 5 | RAG Foundation — Knowledge Base, Document Loader/Parser, Mock Retriever, Context Builder, Search Service |
| 6 | MCP Foundation — Tool Registry, Request Router, MCP Server, Health Check, four mock tools |
| 7 | Multi-Agent Foundation — Agent Registry, Agent Factory, six mock agents, mock messaging, Health Check, Agent Service |
| 8 | AI Evaluation Framework — Accuracy/Latency scoring, Evaluation Reports, Mock Dataset, Prompt Evaluator, Evaluation Service |
| 9 | **Enterprise Integration** — `AIWorkflowService` (chains all five modules above into one call), `PlatformHealthChecker` (a unified health report), one new HTTP endpoint (`GET /api/v1/ai/platform/health`), end-to-end integration tests |

**393 automated tests pass** (cumulative, `pytest`). Every AI capability remains explicitly mock-based end to end — no real vendor LLM, no real vector database, no real MCP transport, no real AI-model-driven agent, no real LLM evaluation service, and no Kafka/database change was ever introduced from the `ai/` layer. See `ai/README.md` for the full technical picture and `docs/release/SPRINT-LOG.md` for the sprint-by-sprint narrative.

**Separately, and NOT resolved by this release:** the underlying OMS360 v1.2 business platform (`app/` — Customer Order Management, Inventory, Kafka Event Processing, Delivery, etc.) has a **spot-verified baseline** (DEC-0011) but has never completed the full QA/regression pass against `docs/qa/QA-STANDARDS.md` §9–10 — this remains a distinct, open item tracked since Sprint 1 (see `docs/governance/RISK-REGISTER.md` RISK-006 and the open item at the end of `docs/governance/DECISION-LOG.md`). The AI Enterprise Platform sprint sequence (1–9) never took on that separate scope.

## Folder Structure

```
Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform/
│
├── docs/
│   ├── architecture/   # System & feature architecture, API/DB/Kafka specs, folder standard
│   ├── business/       # Business requirements, user stories
│   ├── governance/      # Charter, master memory, decisions, standards, module status, risk, change log
│   ├── qa/               # QA standards + AI Chatbot QA suite
│   ├── roadmap/          # Phase 1–4 delivery plan
│   ├── release/          # Sprint/release narrative log
│   └── wiki/              # Navigation index — start here for finding any document
│
├── backend/              # (empty — reserved; the real FastAPI app root is `app/`, see docs/governance/MASTER-PROJECT-MEMORY.md §4)
├── frontend/             # (empty — reserved for the Operations Dashboard frontend)
├── app/                   # OMS360 v1.2 business platform (orders, inventory, kitchen, delivery, Kafka, dashboards) — spot-verified baseline, see RISK-006
├── ai/                     # AI Enterprise Platform — COMPLETE as of v1.0.0 (Sprint 9)
│   ├── providers/            # Provider Framework (Sprint 2 + 4) — BaseProvider, ProviderRegistry, MockAIProvider, ProviderFactory, ProviderHealthChecker
│   ├── services/               # AIService, ServiceRegistry, ServiceFactory, AIHealthService, AIChatService
│   ├── runtime/                  # Env-var-native RuntimeConfiguration, validation, loader
│   ├── rag/                        # RAG Foundation (Sprint 1 + 5) — Knowledge Base, Loader, Parser, Mock Retriever, Context Builder, Search Service
│   ├── mcp/                         # MCP Foundation (Sprint 1 + 6) — Tool Registry, Request Router, MCP Server, Health Check, 4 mock tools
│   ├── agents/                       # Multi-Agent Foundation (Sprint 1 + 7 + 9) — Registry, Factory, Orchestrator, 6 mock agents, mock messaging, Agent Service
│   ├── evals/                         # AI Evaluation Framework (Sprint 1 + 8) — Accuracy/Latency scoring, Reports, Mock Dataset, Prompt Evaluator, Evaluation Service
│   ├── integration/                    # Enterprise Integration (Sprint 9) — AIWorkflowService, PlatformHealthChecker
│   ├── prompts/                          # PromptLoader (template loading + variable validation)
│   └── models/                             # (reserved — empty, no schema needed yet)
│
├── database/              # NOT empty - the master schema + demo data: oms360_schema.sql (source of truth,
│                           #   applied automatically by docker-compose.yml's mysql init-script mount),
│                           #   demo_seed.sql, demo_reset.sql. `migrations/` (repo root) holds the two
│                           #   additive migrations (002_add_audit_trail.sql, 003_add_inventory_ledger.sql)
│                           #   that layer on top of this schema.
├── kafka/                  # (empty — reserved for topic/schema definitions beyond app/'s existing config)
├── docker/                  # docker/docker-compose.app.yml only - a legacy/optional file, explicitly
│                           #   unused by START/STOP/RESTART_OMS360.bat as of the 2026-07-21/22 infra
│                           #   fixes. The real `Dockerfile` and `docker-compose.yml` live at repo root.
├── monitoring/                # (empty — reserved for observability config beyond app/'s existing `/health` `/metrics`)
├── tests/                     # Full test suite — tests/ai/ (Sprint 1-9 AI layer unit tests), tests/api/ai/ (API route tests), tests/integration/ (Sprint 9 end-to-end tests), plus the original app/ test suite
├── scripts/                    # PowerShell/ops scripts
├── release/                     # (empty — reserved for built release archives)
├── backup/                       # Versioned sprint-code backups (backup/OMS360_v<version>_Sprint<N>.zip, latest-only retention) — see docs/governance/DECISION-LOG.md DEC-0013
│
├── README.md                # this file
├── PROJECT_CONTEXT.md         # session-start context primer
└── VERSION-HISTORY.md          # semantic version history
```

`backend/`, `frontend/`, `kafka/` (except the one legacy compose file), `monitoring/`, and `release/` remain intentionally empty — structure only, no placeholder files — per the original Sprint 0 folder-reorg instruction. `database/` is populated with the real master schema and demo data (see above) — this line was corrected on 2026-07-22 after the folder was found to actually contain `oms360_schema.sql`/`demo_seed.sql`/`demo_reset.sql`, not to be empty. `ai/`, `tests/`, `scripts/`, and `backup/` are now populated, as described above.

## Backend Stability Audit (2026-07-22)

A full backend/Docker/DB audit found and fixed several defects that were preventing the application from starting or serving correct data — see `docs/governance/DECISION-LOG.md` for the full entry. Summary: `app/models.py` had an undefined-name crash on import (the app could not start at all), three ORM columns were mapped to database column names that don't exist in `database/oms360_schema.sql` (`grand_total`, `created_at`, `cooking_status`), and `docker-compose.yml`'s MySQL init-script mount pointed at a nonexistent path, so the master schema was likely never actually applied to the `oms360_mysql_data` volume. All four are fixed in code/config only — `database/oms360_schema.sql` itself was not modified, per the standing "database is the source of truth" instruction.

## Where To Start

1. **New session / new contributor:** read `PROJECT_CONTEXT.md` first.
2. **Looking for a specific document:** `docs/wiki/PROJECT-WIKI.md` indexes everything.
3. **Want the full project state (vision, stack, architecture, standards, known issues):** `docs/governance/MASTER-PROJECT-MEMORY.md`.
4. **Want to know what's built vs. pending:** `docs/governance/MODULE-STATUS.md`.
5. **Want the AI layer's technical detail:** `ai/README.md`, plus each module's own README (`ai/providers/README.md`, `ai/rag/README.md`, `ai/mcp/README.md`, `ai/agents/README.md`, `ai/evals/README.md`, `ai/integration/README.md`).
6. **Want the sprint-by-sprint build narrative:** `docs/release/SPRINT-LOG.md`.
7. **Want the roadmap:** `docs/roadmap/PROJECT-ROADMAP.md`.

## Governance

This project follows a strict documentation-first, enterprise-standards process defined in `docs/governance/PROJECT-CHARTER.md`. In short: no code is written without reviewing prior artifacts first, every change updates documentation and the change log, all decisions are recorded permanently in `docs/governance/DECISION-LOG.md`, and nothing is marked "Complete" without verification.

---

*See `VERSION-HISTORY.md` for release history and `FINAL_RELEASE_REPORT.md` for the v1.0.0 completion report.*

# PROJECT-FOLDER-STANDARD.md — OMS-360

> **Superseded at the top level (2026-07-19, DEC-0008):** the project's actual top-level enterprise structure is now defined by the official `Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform/` layout (see root `README.md` and `PROJECT_CONTEXT.md`, and `docs/governance/MASTER-PROJECT-MEMORY.md` §4) — `docs/`, `backend/`, `frontend/`, `ai/`, `database/`, `kafka/`, `docker/`, `monitoring/`, `tests/`, `scripts/`, `release/`, `backups/`. The proposed layout below (originally written as a full repo root under `oms360/`) should now be read as a proposal for **what goes inside `backend/` specifically** — its `backend/app/...` subtree is still a reasonable candidate structure, but it has not yet been reconciled against the real `OMS360_v1.2_Production_Release.zip` layout (per the received architecture doc: `app/routes`, `app/services`, `app/messaging`, `app/static`, `migrations/`). Do not treat the layout below as authoritative for anything outside `backend/` until this reconciliation happens in Sprint 1.

This is the authoritative enterprise folder structure for the parts it covers. **No module may violate this structure.** Any deviation requires a logged decision in `docs/governance/DECISION-LOG.md` before it is implemented, and this document must be updated in the same change.

> Status: baseline structure defined in Sprint 0, ahead of first scaffold. To be confirmed/finalized against the actual repo location decision (open item in `docs/governance/DECISION-LOG.md`) at the start of Sprint 1, and updated here once scaffolded.

## Proposed `backend/` Internal Layout (originally drafted as a full repo root — see note above)

```
oms360/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, router registration
│   │   ├── core/                    # config, logging, exception handlers, security
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── orders/          # Customer Order Management
│   │   │       ├── restaurants/     # Restaurant Management
│   │   │       ├── menus/           # Menu Management
│   │   │       ├── inventory/       # Inventory Management
│   │   │       ├── kitchen/         # Kitchen Processing
│   │   │       ├── payments/        # Payment Processing
│   │   │       ├── delivery/        # Delivery Management
│   │   │       ├── notifications/   # Notification Service
│   │   │       ├── health/          # Health Monitoring
│   │   │       ├── metrics/         # Metrics Monitoring
│   │   │       └── audit/           # Audit Trail
│   │   ├── domain/                  # domain models / business logic per module
│   │   ├── db/
│   │   │   ├── models/              # ORM models
│   │   │   └── migrations/          # Alembic migrations
│   │   ├── events/
│   │   │   ├── producers/           # Kafka producers
│   │   │   ├── consumers/           # Kafka consumers
│   │   │   ├── schemas/             # event payload schemas (versioned)
│   │   │   └── dlq/                 # DLQ handling / reprocessing tools
│   │   └── services/                # cross-module orchestration services
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   └── e2e/
│   ├── Dockerfile
│   └── requirements.txt / pyproject.toml
├── dashboard/                        # React Operations Dashboard
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/                 # typed API client
│   │   └── pages/
│   ├── tests/
│   └── Dockerfile
├── scripts/                          # PowerShell / ops scripts
├── docs/
│   ├── api/                          # curated API documentation
│   ├── database/                     # DB schema documentation, ER diagrams
│   └── architecture/                 # architecture diagrams, AD礼 if any
├── docker-compose.yml
├── README.md
└── CHANGELOG.md
```

## Rules

1. Each domain module owns exactly one directory under `backend/app/api/v1/` and, where applicable, a matching `domain/`, `db/models/`, and `events/` presence — no cross-module code embedded in another module's folder.
2. Tests mirror source structure 1:1 (see `docs/qa/QA-STANDARDS.md` §3).
3. No module introduces a new top-level directory without a logged Decision Log entry.
4. Kafka event schemas live centrally under `events/schemas/`, versioned, shared by both producers and consumers — never duplicated per-module.
5. All documentation produced per module (Rule 7 of the Project Charter) lands under `docs/api/`, `docs/database/`, or the module's own `README.md` section — not scattered ad hoc.
6. This structure is confirmed at the start of Sprint 1 when the repository is actually created, and this document is updated to reflect the confirmed, real structure (not just the proposal) at that point.

---

*Last updated: 2026-07-19 — Sprint 0 (continued, folder reorg — top-level scope note added; proposed `backend/` baseline still pending Sprint 1 confirmation against the real codebase).*

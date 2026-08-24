# 09 — API Test Cases — OMS-360

**Consolidated:** 2026-08-04 (renumbered from `docs/API_Test_Cases.md`,
content unchanged). Primary content is the real, executable V1
Postman/Newman collection built this project. The separate, unbuilt V2
chatbot API test cases are covered in §2 below — originally sourced from
`docs/qa/APITEST-01-...`, that folder is now retired (2026-08-04 final
documentation cleanup).

## 1. V1 — Real, Executable API Test Suite (Newman/Postman)

Generated directly from live FastAPI route source
(`app/routes/*.py`, `app/api/ai/*.py`) — no fabricated or placeholder
APIs. Full collection: `postman/collection/OMS360.postman_collection.json`.
Environment: `postman/environment/OMS360.postman_environment.json`.

| Folder | Requests | Notes |
|---|---|---|
| 01 - Health & Metrics | 4 | `/`, `/version`, `/health`, `/metrics` |
| 02 - Orders | 4 | create/list/get/audit — creates a real order and chains `order_id` |
| 03 - Inventory | 9 | list/low-stock/out-of-stock/alerts/history/get/restock/update/create — chains `item_id` |
| 04 - Dashboard | 8 | Operations + Monitoring Center aggregate JSON endpoints |
| 05 - AI Runtime | 8 | 7 endpoints, `/config` exercised twice (default + `?capability=`) |
| 06 - AI Copilot | 18 | business Q&A, intents, executive summary, insights, root cause, QA/docs/learning assistants — chains `intent` and `learning_topic` |
| 07 - Dashboard Pages (HTML Smoke) | 5 | registered page routes that serve HTML, not JSON — status-code checks only |

**51 JSON API requests** (50 unique endpoints — `/api/v1/ai/config` tested
twice, plain and with `?capability=rag_enabled`) **+ 5 HTML smoke checks =
56 requests, 168 `pm.test()` assertions.**

The key V1 order/validation assertions this collection exercises are
detailed as individual test cases in `docs/07_Test_Plan.md` §2 (API-01..11)
and `docs/08_Test_Cases.md`'s "V1 API" / "V1 Negative" / "V1 Boundary"
tables — not re-typed per-request here since the collection itself (168
live assertions) is the executable source of truth.

### 1.1 How to Run

```bat
Setup_QA_Environment.bat   REM one-time
START_OMS360.bat           REM start the stack (separately)
Run_QA_Pipeline.bat        REM verify -> Newman -> pytest -> Allure report
```

Or Newman only: `cd postman && run-newman.bat`. Reports:
`postman/reports/` (CLI/JSON/HTML Extra/JUnit XML) and
`allure-report/index.html` (open via `allure open allure-report`).
Full detail: `docs/17_Newman_Setup.md`, `docs/18_Allure_Setup.md`.

### 1.2 Variable Chaining

The environment starts with `item_id=ITEM-BURGER`, `intent=pending_orders`,
and `learning_topic=architecture` as safe defaults (real seed-data
values), and `order_id` empty. During a run, list/catalog requests capture
real IDs from live responses into these variables for downstream detail
requests.

---

## 2. V2 — AI Customer Support Chatbot API Test Cases (documented, not built)

Full table: `docs/08_Test_Cases.md`, "V2 Chatbot API Test" section (19
cases, API-01..19, originally sourced from
`docs/qa/APITEST-01-AI-Customer-Support-Chatbot_v1.1.md`, folder retired
2026-08-04).
Covers `POST /api/v1/chatbot/message`, `GET /api/v1/chatbot/{id}/history`,
`GET /api/v1/dashboard/ai-escalations`, and
`POST /api/v1/chatbot/escalations/{id}/resolve` — none of which exist in
the codebase yet. Notable design intent for when this is built: every
test hitting the LLM path should run against a **mock provider** in CI
(deterministic canned tool responses); API-18/19 are regression checks
proving the "kill switch" and "zero regression to existing orders/
dashboard" guarantees hold.

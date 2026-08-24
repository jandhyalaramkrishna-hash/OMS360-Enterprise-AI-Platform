# 02 — Business Requirements Specification (BRS)

**Project:** Project-5-OMS360-Food-Delivery-AI-Enterprise-Platform
**Document owner:** Product Owner / QA Lead (Ram)
**Last consolidated:** 2026-08-04 (documentation reorganization — renumbered from `docs/BRS.md`, content unchanged)

This is the canonical Business Requirements Specification for the project.
It consolidates business requirements previously scattered across
`docs/business/BR-01-AI-Customer-Support-Chatbot_v1.1.md`,
`docs/business/US-01-AI-Customer-Support-Chatbot_v1.1.md`, the project
description, and `README.md` into one document. Those source documents are
left in place (they hold full V2-feature-level detail this BRS summarizes,
not duplicates of each other) — this file is the single place to start.

The project has **three distinct lines of work** with different build
status. Every requirement below is labeled accordingly so nothing here is
mistaken for something it isn't:

| Line | Status | Section |
|---|---|---|
| **V1 — OMS-360 Business Platform** (`app/`) | **Built, running code.** Spot-verified baseline; full regression pass still open. | §1 |
| **AI Enterprise Platform / AI Copilot** (`ai/`) | **Built.** 393+ automated tests passing, mock-based throughout (no real vendor LLM). Development on this line closed at v1.0.0. | §2 |
| **V2 — AI Customer Support Chatbot** | **Documented only — zero lines of code.** Full BRD/architecture/QA suite exists; status "Documentation Complete, Pending Integration." | §3 |

---

## 1. V1 — OMS-360 Business Platform

### 1.1 Problem Statement

Manual or loosely-integrated food-delivery order management does not
scale reliably: orders get lost between kitchen and delivery handoffs,
stock isn't validated in real time, failures aren't retried or surfaced,
and operators have no live visibility into what's happening across the
order lifecycle. OMS-360 exists to prove out a production-style,
event-driven answer to that problem using a real, running stack (FastAPI,
Apache Kafka, MySQL, Docker).

### 1.2 Business Objectives

| ID | Objective | Success Metric |
|---|---|---|
| BRS-V1-1 | Automate the complete order lifecycle end to end | An order placed via the API reaches `DELIVERED` with no manual intervention, per `docs/07_Test_Plan.md` FUNC-03/04 |
| BRS-V1-2 | Guarantee reliable, once-only order processing under failure | Duplicate submissions rejected (idempotency), stock races resolved correctly (row locking), Kafka failures land in a DLQ rather than being silently lost |
| BRS-V1-3 | Give operators real-time visibility | Operations Center and Monitoring Center dashboards refresh every 6s with live KPIs, alerts, and health status |
| BRS-V1-4 | Make every state transition auditable | `order_audit_trail` records every stage of every order (`GET /api/v1/orders/{id}/audit`) |
| BRS-V1-5 | Keep the system observable and operable | `GET /health` and `GET /metrics` report dependency and runtime health at all times |
| BRS-V1-6 | Prove reliability engineering patterns, not just happy-path code | Retry + DLQ handling, structured logging, idempotent processing, and transaction management are all implemented and testable, not aspirational |

### 1.3 In-Scope Business Modules (from the project charter)

Customer Order Management, Restaurant Management, Menu Management,
Inventory Management, Kitchen Processing, Payment Processing, Kafka Event
Processing, Delivery Management, Notification Service, Health Monitoring,
Metrics Monitoring, Audit Trail, Retry & Dead Letter Queue (DLQ),
Operations Dashboard, API Documentation (Swagger/OpenAPI).

**Built and exercised by the current test/QA tooling:** Customer Order
Management, Inventory Management, Kitchen/Delivery status progression (via
the Kafka-driven order lifecycle), Health/Metrics Monitoring, Audit Trail,
Operations/Monitoring/Inventory/AI-Copilot dashboards, API documentation.

**Present in the schema/architecture but with no dedicated module-level
test coverage yet** (each currently exists only as a step embedded inside
the order-lifecycle flow, not as its own tested unit): Restaurant
Management, Menu Management, Payment Processing (beyond
`payment_status` transitions), Notification Service, Retry/DLQ as a
standalone module. See `docs/10_RTM.md` for the exact coverage picture and
`docs/08_Test_Cases.md`'s gap notes for why these weren't fabricated.

### 1.4 Stakeholders

| Stakeholder | Interest |
|---|---|
| Customer | Order placed correctly, tracked accurately, delivered reliably |
| Kitchen Staff / Chef | Clear, correctly-sequenced view of what to prepare |
| Delivery Partner | Correct dispatch information |
| Ops/Support Team | Live dashboards, alerting on failures |
| Engineering/SRE | Health/metrics, DLQ visibility, structured logs |
| Inventory Manager | Real-time stock, low-stock/out-of-stock alerts |
| QA | A system whose behavior can be independently verified — the reason this QA doc set and the Newman/Allure/Jenkins pipeline exist |

### 1.5 Out of Scope for V1

Real payment gateway integration (payment is simulated), real SMS/email
notification delivery (feature-flagged off, logs what it would send), live
GPS tracking (client-side simulation only — no schema columns for real
telemetry), authentication/authorization (none implemented — documented,
known gap), and everything under the Version 2 AI roadmap (§2, §3 below).

### 1.6 Known Business-Level Limitations (carried forward honestly, not hidden)

No authentication on any route. Delivery OTP and live GPS position are
explicitly-labeled client-side simulations. In-memory metrics reset on
process restart. Idempotency/duplicate-order detection uses an in-process
TTL cache — does not survive a process restart or work across multiple app
instances. Source: `docs/FINAL_RELEASE_REPORT.md` §4, `docs/12_Test_Summary_Report.md`.

---

## 2. AI Enterprise Platform / AI Copilot (`ai/`) — Built

### 2.1 Business Objective

Prove that AI capability (RAG, MCP tool-calling, multi-agent orchestration,
evaluation) can be layered onto a real production system additively —
gated behind feature flags, degrading gracefully, and never touching the
order-fulfillment critical path — as a foundation for the Version 2
roadmap (AI fraud detection, predictive inventory, ETA prediction, NL-to-SQL,
etc.) listed in the project description.

### 2.2 Delivered (Sprints 1–9, `v1.0.0`, closed)

AI Service Layer scaffolding → Runtime Infrastructure/feature
flags/health/metrics → read-only AI API Layer → Provider Framework
(`MockAIProvider`) → RAG Foundation → MCP Foundation → Multi-Agent
Foundation → AI Evaluation Framework → Enterprise Integration
(`AIWorkflowService`, `PlatformHealthChecker`, `GET /api/v1/ai/platform/health`).
**393/393 automated tests pass** (real, executed — see `docs/12_Test_Summary_Report.md`).
Explicitly mock-based throughout: no real vendor LLM, vector DB, MCP
transport, agent runtime, or evaluation service — by design, disclosed,
not a gap to be quietly filled later without a new scoped version.

### 2.3 Success Metric

Zero regressions to `app/`'s order-fulfillment flow attributable to the
`ai/` layer, across all nine sprints — verified by `tests/ai/test_agents.py`
and `tests/ai/test_evals.py` (Sprint 1) still passing unmodified nine
sprints later.

---

## 3. V2 — AI Customer Support Chatbot — Documented, Not Built

Full detail: `docs/business/BR-01-AI-Customer-Support-Chatbot_v1.1.md`
(source of this section) and `docs/business/US-01-AI-Customer-Support-Chatbot_v1.1.md`
(user stories). Summarized here for completeness of this BRS; not re-typed
in full to avoid a second editable copy drifting from the original.

### 3.1 Problem Statement

Support volume for repetitive order-status/refund/cancellation questions
has no self-service deflection today — every question consumes a human
agent's time regardless of complexity.

### 3.2 Business Objectives

| ID | Objective | Success Metric |
|---|---|---|
| BRS-V2-1 | Deflect repetitive status/ETA/refund questions | ≥ 40% of chatbot conversations resolved without escalation |
| BRS-V2-2 | 24/7 availability | Uptime independent of agent shift hours |
| BRS-V2-3 | Never give an incorrect order fact | 0 confirmed hallucinated-fact incidents in production |
| BRS-V2-4 | Escalate hard cases with full context | 100% of escalations carry conversation_id + order_id + reason |
| BRS-V2-5 | Zero impact on order fulfillment if AI misbehaves | Feature flag off = zero behavioral change to `order_service`/`consumer.py` |

### 3.3 In Scope (when built)

Order status / delivery ETA / cancellation eligibility / refund status
Q&A; general FAQ from a controlled knowledge base; escalation to human
agents via the existing Operations dashboard pattern; conversation logging
for QA review.

### 3.4 Out of Scope (this version, when built)

Cannot cancel/refund/modify an order (read-only always); text/chat only,
no voice; no multi-language guarantee; no custom model fine-tuning (uses
the existing `AI_PROVIDER` config with tool-calling); not a replacement
for the existing Operations dashboard, an additional escalation source
feeding it.

### 3.5 Key User Stories (full acceptance criteria in US-01)

Customer: ask order status, ask delivery ETA, ask cancellation
eligibility, ask refund status, ask general FAQ, request human escalation.
Support Agent: see AI-escalated conversations with context on the
Operations dashboard. QA Engineer: pull full transcript + tool-call trace
for auditability. Engineering/SRE: instant kill switch
(`ai_chatbot_enabled=false`) with zero redeploy, zero downtime to the rest
of OMS360.

### 3.6 Dependencies and Blockers to Build

Requires `orders_master`, `order_audit_trail`, `delivery_status`,
`kitchen_status`, `transactions` (all existing, read-only). Requires an
LLM provider credential in `AI_API_KEY` (currently blank — must be
provisioned before `ai_chatbot_enabled` can be turned on anywhere real).
Requires `ai_features_enabled=true` AND a new `ai_chatbot_enabled`
sub-flag=true (both default false — opt-in only).

### 3.7 Top Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM provider cost overrun at scale | Medium | Medium | Rate limiting, context compression, response length cap |
| Hallucinated order fact reaches a customer | Low (with guard) | High | Post-generation guard — see Feature-01 §11/12 |
| PII sent to a third-party LLM provider | Medium | High | Only order_id/status enums sent, never full address/card data |
| Agents ignore AI escalations | Medium | Medium | Reuses the existing, already-trusted Alerts panel pattern |

---

## 4. Traceability

Every objective ID in this document (`BRS-V1-*`, `BRS-V2-*`) is mapped to
its implementing test cases in `docs/10_RTM.md` (companion spreadsheet:
`docs/RTM.xlsx`). See `docs/03_SRS.md` for the corresponding
functional/non-functional system requirements, and `docs/07_Test_Plan.md`
for how each is actually verified.

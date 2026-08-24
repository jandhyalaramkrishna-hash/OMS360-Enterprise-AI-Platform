# 10 — Requirements Traceability Matrix (RTM)

**New markdown conversion, 2026-08-04**, of `docs/RTM.xlsx` — kept as a
companion spreadsheet artifact alongside this markdown version. Both carry
identical content; `docs/RTM.xlsx` is not being retired.

Maps every requirement in `docs/02_BRS.md` and `docs/03_SRS.md` to the
test case(s) that verify it, and honestly marks **GAP** where no test case
exists yet. This was the first RTM this project had (`TEST_CASE_COVERAGE.md`
previously flagged its absence as a known gap). Full requirement text:
`docs/02_BRS.md`, `docs/03_SRS.md`. GAP rows are honest, not aspirational —
see `TEST_CASE_COVERAGE.md` §Missing Test Cases for why each wasn't
fabricated.

| Requirement ID | Requirement | Module | Product Line | Built? | Test Case ID(s) | Test Document | Coverage Status |
|---|---|---|---|---|---|---|---|
| BRS-V1-1 | Automate the complete order lifecycle end to end | Customer Order Management | V1 | Yes | FUNC-03, FUNC-04, KAFKA-01..05 | `07_Test_Plan.md` | Covered |
| BRS-V1-2 | Guarantee reliable, once-only order processing under failure | Order/Kafka reliability | V1 | Yes | API-03, NEG-03, KAFKA-03/04, BND-06 | `07_Test_Plan.md` | Covered |
| BRS-V1-3 | Give operators real-time visibility | Operations/Monitoring Dashboards | V1 | Yes | DASH-01, DASH-02, DASH-06 | `08_Test_Cases.md` (V1 Dashboard) | Covered (not yet executed) |
| BRS-V1-4 | Make every state transition auditable | Audit Trail | V1 | Yes | FUNC-06 | `07_Test_Plan.md` | Covered |
| BRS-V1-5 | Keep the system observable and operable | Health/Metrics | V1 | Yes | API-08, API-09, Smoke #1/#2 | `07_Test_Plan.md` §6.2 | Covered |
| BRS-V1-6 | Prove reliability engineering patterns (retry/DLQ/idempotency) | Retry & DLQ | V1 | Yes | KAFKA-03/04, API-03 | `07_Test_Plan.md` | Covered |
| FR-01 | Accept a new order, reserve stock atomically | Customer Order Management | V1 | Yes | FUNC-01, Newman '02 Orders' | `07_Test_Plan.md`, `09_API_Test_Cases.md` | Covered |
| FR-02 | Multi-line-item orders, correct grand total | Customer Order Management | V1 | Yes | FUNC-02 | `07_Test_Plan.md` | Covered |
| FR-03 | Advance order via Kafka asynchronously | Kafka Event Processing | V1 | Yes | FUNC-03, KAFKA-01..05 | `07_Test_Plan.md` | Covered (manual only) |
| FR-04 | Reach terminal DELIVERED/PAID state unattended | Order lifecycle | V1 | Yes | FUNC-04 | `07_Test_Plan.md` | Covered |
| FR-05 | Order retrieval by ID | Customer Order Management | V1 | Yes | FUNC-05, API-07 | `07_Test_Plan.md` | Covered |
| FR-06 | Full chronological audit trail per order | Audit Trail | V1 | Yes | FUNC-06 | `07_Test_Plan.md` | Covered |
| FR-07 | Expose current inventory levels | Inventory Management | V1 | Yes | FUNC-07, Newman '03 Inventory' | `07_Test_Plan.md`, `09_API_Test_Cases.md` | Covered |
| FR-08 | Reject duplicate order submissions | Customer Order Management | V1 | Yes | API-03, BND-06 | `07_Test_Plan.md` | Covered |
| FR-09 | Resolve concurrent stock races correctly | Inventory Management | V1 | Yes | NEG-03, BND-05 | `07_Test_Plan.md` | Covered |
| FR-10 | Route unprocessable Kafka events to DLQ | Retry & DLQ | V1 | Yes | KAFKA-03, KAFKA-04 | `07_Test_Plan.md` | Covered (manual only) |
| FR-11 | Serve live operational dashboards | Operations Dashboard | V1 | Yes | DASH-01..06 | `08_Test_Cases.md` (V1 Dashboard) | Covered (not yet executed) |
| MOD-RESTAURANT | Restaurant Management module | Restaurant Management | V1 | Partial (schema only) | — | — | GAP — no dedicated test case, see `TEST_CASE_COVERAGE.md` |
| MOD-MENU | Menu Management module | Menu Management | V1 | Partial (schema only) | — | — | GAP — no dedicated test case |
| MOD-PAYMENT | Payment Processing (beyond payment_status) | Payment Processing | V1 | Partial | FUNC-04 (payment_status only) | `07_Test_Plan.md` | Partial — no payment-gateway-failure test case |
| MOD-NOTIFICATION | Notification Service module | Notification Service | V1 | Yes (flagged off by default) | — | — | GAP — no dedicated test case |
| MOD-KITCHEN | Kitchen Processing (as its own module) | Kitchen Processing | V1 | Yes (embedded in order flow) | FUNC-03, KAFKA-01 | `07_Test_Plan.md` | Partial — only as embedded lifecycle step, no standalone edge cases |
| MOD-DELIVERY | Delivery Management (as its own module) | Delivery Management | V1 | Yes (embedded in order flow) | FUNC-03, FUNC-04 | `07_Test_Plan.md` | Partial — same as Kitchen |
| NFR-01 | Every module has automated coverage before Complete | Governance | V1 | Policy | — | `06_Test_Strategy.md` §1 | Policy — enforced via MODULE-STATUS.md review |
| NFR-02 | Kafka failures retry then DLQ, never silently drop | Retry & DLQ | V1 | Yes | KAFKA-03 | `07_Test_Plan.md` | Covered |
| NFR-03 | /health always 200, degraded deps visible not hidden | Health Monitoring | V1 | Yes | API-08, NEG-05, NEG-06 | `07_Test_Plan.md` | Covered |
| NFR-04 | /metrics exposes counters/response times | Metrics Monitoring | V1 | Yes | API-09 | `07_Test_Plan.md` | Covered |
| NFR-05 | Input validation + parameterized queries only | Security | V1 | Yes | API-04, API-05, API-06, NEG-01, NEG-02, NEG-04 | `07_Test_Plan.md` | Covered |
| NFR-06 | No stack trace leaks on 500 | Security | V1 | Yes | API-10, NEG-05 | `07_Test_Plan.md` | Covered |
| NFR-07 | Baseline load test per module | Performance | V1 | No | — | — | GAP — no performance tooling wired in yet, see `06_Test_Strategy.md` §7 |
| NFR-08 | Structured logging with correlation ID | Logging | V1 | Yes (by design, not test-asserted) | — | — | GAP — no automated test asserts log output/capture |
| NFR-09 | Idempotency-Key prevents duplicate orders | Customer Order Management | V1 | Yes | API-03, BND-06 | `07_Test_Plan.md` | Covered |
| NFR-10 | Full stack runs via docker compose up | Portability | V1 | Yes | Smoke #1-6 | `07_Test_Plan.md` §6.2 | Covered |
| NFR-11 | AI features gated + degrade gracefully | AI Enterprise Platform | AI Platform | Yes | tests/ai/* (393 automated tests) | `12_Test_Summary_Report.md` | Covered |
| BRS-V2-1 | Deflect repetitive status/ETA/refund questions | AI Customer Support Chatbot | V2 | No — documented only | TC-01, TC-04, TC-07 | `08_Test_Cases.md` (V2 Chatbot TC) | Spec'd, not executable — feature not built |
| BRS-V2-2 | 24/7 chatbot availability | AI Customer Support Chatbot | V2 | No | — | — | Not applicable until built |
| BRS-V2-3 | Never give an incorrect order fact | AI Customer Support Chatbot | V2 | No | TC-16, TC-13 | `08_Test_Cases.md` (V2 Chatbot TC) | Spec'd, not executable |
| BRS-V2-4 | Escalate hard cases with full context | AI Customer Support Chatbot | V2 | No | TC-10, TC-11, TC-12 | `08_Test_Cases.md` (V2 Chatbot TC) | Spec'd, not executable |
| BRS-V2-5 | Zero impact on order fulfillment if AI misbehaves | AI Customer Support Chatbot | V2 | No | API-18, API-19 (Regression) | `08_Test_Cases.md` (V2 Chatbot API Test) | Spec'd, not executable |

<!-- Consolidated into docs/QA_Documents/ on 2026-08-03. Original remains at docs/qa/TP-01-AI-Customer-Support-Chatbot_v1.1.md. Scope: V2 AI Customer Support Chatbot (documentation-only, not yet built). Content below is an exact copy, unmodified. -->

# QA Test Plan — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## 1. Scope
Covers: `POST /api/v1/chatbot/message`, `GET /api/v1/chatbot/{id}/history`,
`GET /api/v1/dashboard/ai-escalations`,
`POST /api/v1/chatbot/escalations/{id}/resolve`, the 4 new DB tables,
the new `ai.chatbot.escalated` Kafka topic, and the anti-hallucination
guard.

## 2. Test Levels
| Level | Focus |
|---|---|
| Unit | Identity-check logic, guard logic, intent classifier thresholds (isolated, mocked LLM) |
| API/Functional | Full request/response contract for all 4 endpoints |
| Integration | End-to-end: message → tool call → real DB read → reply → DB persisted → (if escalated) Kafka event → dashboard endpoint reflects it |
| AI-specific | Prompt regression, hallucination guard, tool-call correctness, context-window truncation |
| Regression | Confirm zero behavior change to orders/kitchen/delivery/inventory/dashboard when flag is off, and when on |
| Performance | Latency under concurrent conversations, rate-limit correctness |
| Security | Identity binding, prompt injection, PII in logs, data retention |

## 3. Entry Criteria
- `ai_features_enabled` and `ai_chatbot_enabled` togglable via env var
  in the test environment
- Migration `004_add_ai_chatbot_tables.sql` applied to test DB
- A mock/stub LLM provider available for deterministic test runs
  (real provider used only for a smaller "AI Testing" smoke pass)

## 4. Exit Criteria
- 100% of Acceptance Criteria scenarios (Feature-01 doc, Section 5) pass
- 0 open Sev-1/Sev-2 defects
- Regression suite (existing `tests/test_orders.py`, `test_health.py`,
  `test_sql_validation.py`) passes unchanged with the feature both ON and OFF
- Guard-trigger rate on the adversarial test set (Section "AI Testing")
  is 100% (every deliberately-hallucination-inducing prompt is caught)

## 5. Test Environment Matrix
| Env | LLM Provider | Purpose |
|---|---|---|
| Local/CI | Deterministic mock (canned tool-call responses) | Fast, repeatable functional + regression runs |
| Staging | Real provider, low rate limit | AI-specific smoke tests, prompt regression, cost sanity check |

## 6. Risk-Based Prioritization
1. **Highest:** hallucination guard, identity binding (data leakage) — Sev-1 if broken
2. **High:** feature-flag-off fallback (must never break core flow)
3. **Medium:** escalation → dashboard visibility, rate limiting
4. **Lower:** FAQ answer accuracy, conversation summary compression

## 7. Deliverables
- Test Cases (QA/Test Cases)
- API Test Cases (QA/API Testing)
- SQL Validation scripts (QA/SQL Validation)
- Regression checklist (QA/Regression Testing)
- Performance test plan (QA/Performance Testing)
- AI-specific adversarial test set (QA/AI Testing)

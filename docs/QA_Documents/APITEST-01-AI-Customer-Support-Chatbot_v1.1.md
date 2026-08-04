<!-- Consolidated into docs/QA_Documents/ on 2026-08-03. Original remains at docs/qa/APITEST-01-AI-Customer-Support-Chatbot_v1.1.md. Scope: V2 AI Customer Support Chatbot (documentation-only, not yet built). Content below is an exact copy, unmodified. -->

# API Test Cases — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

| ID | Method & Endpoint | Input | Expected Status | Expected Response Assertion |
|---|---|---|---|---|
| API-01 | POST /api/v1/chatbot/message | Valid mobile+order_id+message | 200 | `conversation_id` present, `reply` non-empty string |
| API-02 | POST /api/v1/chatbot/message | Missing `message` field | 422 | error.detail mentions `message` |
| API-03 | POST /api/v1/chatbot/message | `message: ""` | 422 | validation error |
| API-04 | POST /api/v1/chatbot/message | `customer_mobile` invalid format (e.g. "12") | 422 | validation error, same regex as OrderCreatePayload |
| API-05 | POST /api/v1/chatbot/message | `conversation_id` set to a nonexistent ID | 404 | error body present |
| API-06 | POST /api/v1/chatbot/message | mobile/order mismatch (TC-02 scenario) | 200 | `tool_called: null`, reply does not contain order fields |
| API-07 | POST /api/v1/chatbot/message | 21st request in 60s window, same mobile | 429 | Retry-After header or clear rate-limit message |
| API-08 | POST /api/v1/chatbot/message | `ai_chatbot_enabled=false` | 200 | static fallback text, `tool_called: null`, `escalated: false` |
| API-09 | GET /api/v1/chatbot/{conversation_id}/history | Valid, existing conversation_id | 200 | array, oldest-first, each item has `sender`,`message_text`,`created_at` |
| API-10 | GET /api/v1/chatbot/{conversation_id}/history | Nonexistent conversation_id | 404 | error body present |
| API-11 | GET /api/v1/dashboard/ai-escalations | limit=5 | 200 | array length ≤ 5, each item has `escalation_id`,`order_id`,`reason`,`status` |
| API-12 | GET /api/v1/dashboard/ai-escalations | No query params (default limit) | 200 | array returned, no 500 |
| API-13 | POST /api/v1/chatbot/escalations/{id}/resolve | Valid PENDING escalation_id | 200 | `status: "RESOLVED"`, `resolved_at` populated |
| API-14 | POST /api/v1/chatbot/escalations/{id}/resolve | Already-RESOLVED escalation_id | 409 | error body present |
| API-15 | POST /api/v1/chatbot/escalations/{id}/resolve | Nonexistent escalation_id | 404 | error body present |
| API-16 | POST /api/v1/chatbot/message | Malformed JSON body | 422 | FastAPI default validation error shape |
| API-17 | POST /api/v1/chatbot/message | Extremely long message (>1000 chars) | 422 | validation error |
| API-18 | (Regression) POST /api/v1/orders | Standard valid order payload, chatbot flag ON | 201 | Unaffected — identical to pre-chatbot behavior |
| API-19 | (Regression) GET /api/v1/dashboard/kpis | Any state | 200 | Response shape identical to pre-chatbot version (no new required fields) |

## Notes for Automation (e.g. pytest + requests / httpx)
- Every test hitting the LLM path should run against the **mock
  provider** in CI (deterministic canned tool responses) — API-01,
  API-06, API-08, API-16 do not require a real LLM call at all and
  should never be gated on real-provider availability.
- API-08 and the regression rows (API-18/19) are the highest-value
  automated checks to run on every build, since they prove the "kill
  switch" and "zero regression" guarantees hold.

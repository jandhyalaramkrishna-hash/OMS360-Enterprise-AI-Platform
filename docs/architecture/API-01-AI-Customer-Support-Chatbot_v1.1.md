# API Specification — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1 | New router: `app/routes/chatbot.py`, prefix `/api/v1/chatbot`

---

## 1. `POST /api/v1/chatbot/message`
Send a customer message, get an AI reply or a graceful fallback.

**Request body**
```json
{
  "conversation_id": null,
  "customer_mobile": "9123456789",
  "order_id": "ORD-1042",
  "message": "where is my order"
}
```
| Field | Type | Required | Notes |
|---|---|---|---|
| conversation_id | string\|null | No | null starts a new conversation |
| customer_mobile | string | Yes | Regex-validated, same pattern as existing `OrderCreatePayload.mobile` |
| order_id | string\|null | No | Optional context hint; not trusted blindly — always re-verified server-side |
| message | string | Yes | 1–1000 chars |

**Response 200**
```json
{
  "conversation_id": "CONV-88213",
  "reply": "Your order ORD-1042 is out for delivery with Ravi Kumar right now.",
  "intent_detected": "ORDER_STATUS",
  "tool_called": "get_order_status",
  "escalated": false,
  "guard_triggered": false
}
```

**Error responses**
| Status | Condition |
|---|---|
| 422 | Empty message, message > 1000 chars, invalid mobile format |
| 429 | Rate limit exceeded (e.g. > 20 messages/60s per mobile number) |
| 404 | `conversation_id` provided but doesn't exist |
| 200 (not an error) | Feature flag off → still 200, with a static fallback `reply` and `tool_called: null` — deliberately not an error status, since "chatbot is off" isn't a system fault |

---

## 2. `GET /api/v1/chatbot/{conversation_id}/history`
Full transcript, oldest first — mirrors the existing
`GET /api/v1/orders/{order_id}/audit` pattern exactly.

**Response 200**
```json
[
  {
    "message_id": 501,
    "sender": "CUSTOMER",
    "message_text": "where is my order",
    "intent_detected": null,
    "tool_called": null,
    "guard_triggered": false,
    "created_at": "2026-07-18T10:02:11Z"
  },
  {
    "message_id": 502,
    "sender": "AI",
    "message_text": "Your order ORD-1042 is out for delivery with Ravi Kumar right now.",
    "intent_detected": "ORDER_STATUS",
    "tool_called": "get_order_status",
    "guard_triggered": false,
    "created_at": "2026-07-18T10:02:13Z"
  }
]
```
**Error:** 404 if `conversation_id` not found.

---

## 3. `GET /api/v1/dashboard/ai-escalations?limit=`
Appended to the existing `dashboard.py` router (same file, same
prefix, same pattern as `live-orders`/`alerts` — no new router needed
for this one endpoint since it's a dashboard feed, not a chatbot
action).

**Response 200**
```json
[
  {
    "escalation_id": 12,
    "conversation_id": "CONV-88213",
    "order_id": "ORD-1042",
    "reason": "refund dispute / repeated complaint",
    "status": "PENDING",
    "created_at": "2026-07-18T10:05:00Z"
  }
]
```

---

## 4. `POST /api/v1/chatbot/escalations/{escalation_id}/resolve`
**Request body**
```json
{ "assigned_to": "agent_priya" }
```
**Response 200**
```json
{ "escalation_id": 12, "status": "RESOLVED", "resolved_at": "2026-07-18T10:20:00Z" }
```
**Error:** 404 if escalation not found; 409 if already resolved.

---

## 5. Cross-Cutting Contract Rules
- All 4 endpoints are registered but **return the flag-off fallback
  behavior** (not 404/500) if `ai_features_enabled` or
  `ai_chatbot_enabled` is false — consistent with how the rest of
  OMS360 uses `FEATURE_FLAGS` today (a disabled feature responds
  cleanly, it doesn't disappear).
- No existing endpoint's request/response contract changes. This is
  purely additive surface, exactly like Dashboard v1.1's 6 new
  endpoints were additive to `/operations`/`/analytics`.
- Error shape matches the existing global handler:
  `{"error": ..., "detail": ..., "request_id": ...}` — no new error
  format introduced.

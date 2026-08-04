# Functional Flow — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## Sequence (happy path — order status question)
1. Customer → `POST /api/v1/chatbot/message`
   `{ conversation_id: null, customer_mobile: "9123456789", order_id: "ORD-1042", message: "where is my order" }`
2. `chatbot.py` route → checks `settings.FEATURE_FLAGS["ai_features_enabled"]`
   and `ai_chatbot_enabled`. Both true → continue. (Either false →
   short-circuit to static fallback, skip to step 9.)
3. `ai_chatbot_service.py`:
   a. No `conversation_id` given → create new row in
      `ai_chatbot_conversations` (status=OPEN).
   b. Identity check: query `orders_master` for `order_id`, compare
      `mobile`/`mobile_number` to `customer_mobile`. Mismatch → return
      a "please verify your order" reply, log message, **stop** (no
      LLM call).
   c. Load last 6 turns for this conversation (none, since new).
4. Assemble LLM request: system prompt + tool schemas + message.
5. LLM responds with a tool call: `get_order_status(order_id="ORD-1042")`.
6. Service executes the **existing** read query (same pattern as
   `GET /api/v1/orders/{order_id}`) — no new business logic, read-only,
   reuses `models.OrdersMaster`.
7. Tool result returned to LLM → LLM produces final natural-language reply.
8. Guard check (Section 11 of Feature-01 doc): reply mentions a status
   word AND `get_order_status` was called this turn → **passes**.
9. Persist: customer message row + AI reply row → `ai_chatbot_messages`.
   Update `ai_chatbot_conversations.last_message_at`.
10. Response returned to customer with `conversation_id` (client
    reuses this ID for the next message in the same conversation).

## Sequence (escalation path)
1–4 same as above, but message is "This is the 3rd time it's late, I
want my money back now."
5. LLM classifies this as a dispute/complaint (via system-prompt rule,
   not a tool — this is intent classification within the same call).
6. Service sets `ai_chatbot_conversations.status = ESCALATED`.
7. Insert `ai_chatbot_escalations` row (reason = "refund dispute /
   repeated complaint", order_id if known).
8. Publish Kafka `ai.chatbot.escalated` (payload: conversation_id,
   order_id, reason, mobile — same envelope shape as existing events
   like `order.created`, for consistency).
9. Reply to customer acknowledges escalation + sets expectation
   ("A support specialist will contact you within X hours").
10. Operations dashboard's new "AI Escalations" panel picks this up on
    its next poll via `GET /api/v1/dashboard/ai-escalations`.

## Sequence (feature flag off / provider down)
1. Route or service detects flag off / provider timeout.
2. No LLM call is attempted (flag off) or the LLM call is abandoned
   after timeout (provider down).
3. A static, pre-written fallback reply is returned:
   *"Our chat assistant is temporarily unavailable. Please reach
   support at <existing support channel>."*
4. This turn is still logged (sender=AI, tool_called=null,
   intent_detected=null) so QA/analytics can see fallback frequency.
5. **No other part of OMS360 is touched** — `order_service.py`,
   `consumer.py`, Kafka order-lifecycle topics, kitchen/delivery flow
   all continue exactly as before. This is the core "AI is additive,
   never a dependency" guarantee from Architecture v1.0 Section 8.

## Where this plugs into the existing architecture (no redesign)
- Reuses the exact same "route → service → ORM" layering as every
  existing module.
- Reuses the exact dashboard polling pattern (`GET` + 6s `setInterval`)
  for the new Escalations panel — no new frontend pattern introduced.
- Reuses the Kafka event envelope shape and topic-naming convention
  (`domain.action`) already used by `order.created`, `payment.failed`, etc.
- Reuses `FEATURE_FLAGS` dict already defined in `config.py` instead of
  inventing a new config mechanism.

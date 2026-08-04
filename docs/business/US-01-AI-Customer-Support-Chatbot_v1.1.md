# User Stories — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## US-1 (Customer — Order Status)
**As a** customer, **I want to** ask the chatbot where my order is,
**so that** I don't have to call support for a simple status check.
- AC: Bot must call `get_order_status` before stating any status.
- AC: If order not found, bot says so and asks the customer to
  double-check the order ID, never guesses.

## US-2 (Customer — Delivery ETA)
**As a** customer, **I want to** ask how long my delivery will take,
**so that** I can plan around it.
- AC: ETA is only reported if `get_delivery_eta` returns a value;
  otherwise the bot says it can't estimate yet (e.g. order not yet
  dispatched) rather than making one up.

## US-3 (Customer — Cancellation)
**As a** customer, **I want to** ask if I can still cancel my order,
**so that** I know my options before it's too late.
- AC: Eligibility is computed from real `order_status`/`kitchen_status`
  (e.g. eligible only while `RECEIVED`, not once `PREPARING` has
  started) via `check_cancellation_eligibility` — bot never invents
  a cancellation window.
- AC: Bot explains eligibility but does not perform the cancellation.

## US-4 (Customer — Refund Status)
**As a** customer, **I want to** ask when my refund will arrive,
**so that** I'm not left wondering.
- AC: Refund facts sourced only from `transactions`/`payment_status`
  via `get_refund_status`.
- AC: If a customer disputes the refund amount, this is an automatic
  escalation trigger, not something the bot argues about.

## US-5 (Customer — General FAQ)
**As a** customer, **I want to** ask general questions (delivery
charges, accepted payment methods, how cancellation policy works),
**so that** I get quick answers without an agent.
- AC: Answered only from `ai_faq_knowledge_base` via `search_faq`; if
  no match, bot says it doesn't have that information.

## US-6 (Customer — Escalation)
**As a** customer, **I want to** be connected to a human when the bot
can't help or I explicitly ask for one,
**so that** I'm never stuck talking to a bot that can't solve my
problem.
- AC: Escalation creates a row in `ai_chatbot_escalations` and
  publishes `ai.chatbot.escalated`.
- AC: Bot tells the customer an escalation has happened, not just
  "goodbye."

## US-7 (Support Agent — Escalation Queue)
**As a** support/ops agent, **I want to** see AI-escalated
conversations on the Operations dashboard with the reason and order
context attached,
**so that** I can prioritize and resolve them without re-asking the
customer everything from scratch.
- AC: New "AI Escalations" panel shows conversation_id, order_id (if
  any), reason, and time, refreshed on the existing 6-second poll.
- AC: Agent can mark an escalation resolved via
  `POST /api/v1/chatbot/escalations/{id}/resolve`.

## US-8 (QA Engineer — Auditability)
**As a** QA engineer, **I want to** pull the full transcript and the
tool-call trace of any conversation,
**so that** I can verify every factual claim the bot made was
actually backed by a real tool result.
- AC: `GET /api/v1/chatbot/{conversation_id}/history` returns every
  message with `tool_called` and `guard_triggered` fields intact.

## US-9 (Engineering/SRE — Kill Switch)
**As an** engineer, **I want to** disable the chatbot instantly without
a redeploy if it misbehaves in production,
**so that** a bad AI response never becomes a prolonged incident.
- AC: Setting `ai_chatbot_enabled=false` (env var) takes effect on the
  next request with zero code change, zero downtime to the rest of
  OMS360.

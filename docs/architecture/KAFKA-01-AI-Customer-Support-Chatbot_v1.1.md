# Kafka / Event Changes — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## New Topic: `ai.chatbot.escalated`
Follows the existing `domain.action` naming convention used by
`order.created`, `payment.failed`, `kitchen.accepted`, etc. — added to
`KafkaTopics` enum in `app/core/enums.py` and `TOPIC_*` constants in
`app/config.py`, same pattern as every existing topic.

**Producer:** `ai_chatbot_service.py`, published synchronously right
after the `ai_chatbot_escalations` row commits (mirrors how
`order_service.create_order` publishes `order.created` right after its
commit).

**Payload envelope (matches existing event shape):**
```json
{
  "event_type": "AI_CHATBOT_ESCALATED",
  "conversation_id": "CONV-88213",
  "order_id": "ORD-1042",
  "customer_mobile": "9123456789",
  "reason": "refund dispute / repeated complaint",
  "escalation_id": 12,
  "timestamp": "2026-07-18T10:05:00Z"
}
```

**Consumers:**
1. **Operations dashboard** — does *not* consume Kafka directly (the
   dashboards are poll-based, matching the existing architecture);
   instead reads the `ai_chatbot_escalations` table via the new
   `GET /api/v1/dashboard/ai-escalations` endpoint. The Kafka event is
   for downstream systems (notification pipeline, analytics), not the
   dashboard's own refresh — same separation of concerns as the rest
   of the dashboard endpoints, which are read-only DB queries, not
   Kafka consumers.
2. **`notification_service.py`** (existing file) — optionally extended
   to send an email/Slack ping to the ops team when this event fires,
   gated behind the existing `FEATURE_FLAGS["notifications_enabled"]`
   flag (already off by default) — reuses the existing notification
   gating pattern rather than inventing a new one.

## Retry / DLQ Behavior
Reuses the existing producer (`app/messaging/producer.py`) as-is — its
existing retry-then-DLQ behavior (`MAX_RETRY_COUNT`, falls back to
`dlq_orders`... **note:** `dlq_orders` is order-pipeline-specific by
schema (`order_id`, `transaction_id` columns); a failed
`ai.chatbot.escalated` publish instead falls back to logging a
`WARNING` and leaving the `ai_chatbot_escalations` row as `PENDING`
with no Kafka event sent — **the DB row is the source of truth for the
Operations dashboard**, so a lost Kafka event degrades notification
speed, not correctness. This is a deliberate, documented difference
from the order pipeline, where Kafka is the source of truth for
downstream state changes.

## No Other Topics Touched
`order.created`, `payment.completed/failed`, `kitchen.*`,
`delivery.*`, `inventory.updated` are all completely unmodified. The
chatbot never publishes to or consumes from any order-lifecycle topic
— it only reads order data via direct DB queries (through existing
read patterns), keeping this feature fully decoupled from the
fulfillment event stream.

## Kafka Change Summary Table
| Topic | New/Existing | Producer | Consumer |
|---|---|---|---|
| `ai.chatbot.escalated` | **New** | ai_chatbot_service.py | notification_service.py (optional), analytics (future) |

# Database Design — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1 | Migration: `migrations/004_add_ai_chatbot_tables.sql`

## Design Principles Applied
- Additive only — `CREATE TABLE IF NOT EXISTS`, matching the exact
  style of `migrations/002_add_audit_trail.sql` and
  `migrations/003_add_inventory_ledger.sql`.
- `ai_chatbot_conversations.order_id` is a **nullable FK with
  `ON DELETE SET NULL`** (not CASCADE) — deliberately different from
  `order_items`/`kitchen_status`/`delivery_status`, which cascade,
  because chat history must survive even if an order row is ever
  purged, for support-quality auditing.
- No existing table gets a new column. `orders_master.fraud_status`
  and other existing columns are read-only inputs to this feature,
  never written by it.

## Entity-Relationship Summary
```
orders_master (existing, unchanged)
      │ 1
      │
      │ 0..1  (nullable FK, ON DELETE SET NULL)
ai_chatbot_conversations ──────┐
      │ 1                      │ 1
      │                        │
      │ many                   │ many
ai_chatbot_messages      ai_chatbot_escalations

ai_faq_knowledge_base  (standalone, no FK — grounding content only)
```

## Table: `ai_chatbot_conversations`
| Column | Type | Notes |
|---|---|---|
| conversation_id | VARCHAR(50) PK | e.g. `CONV-88213` |
| customer_mobile | VARCHAR(20) | indexed |
| order_id | VARCHAR(50) NULL | FK → orders_master, SET NULL on delete |
| status | VARCHAR(20) | OPEN / RESOLVED / ESCALATED |
| channel | VARCHAR(20) | WEB_WIDGET / MOBILE_APP (future) |
| started_at | TIMESTAMP | |
| last_message_at | TIMESTAMP | auto-updates |

## Table: `ai_chatbot_messages`
| Column | Type | Notes |
|---|---|---|
| message_id | BIGINT PK AUTO_INCREMENT | |
| conversation_id | VARCHAR(50) | FK, CASCADE (messages belong to their conversation) |
| sender | VARCHAR(10) | CUSTOMER / AI / AGENT |
| message_text | TEXT | see Security notes — PII redaction on write |
| intent_detected | VARCHAR(50) NULL | ORDER_STATUS / REFUND / CANCEL / FAQ / COMPLAINT / OTHER |
| tool_called | VARCHAR(50) NULL | null if no tool was invoked this turn |
| guard_triggered | BOOLEAN | true if the anti-hallucination guard discarded a draft reply |
| created_at | TIMESTAMP | |

## Table: `ai_chatbot_escalations`
| Column | Type | Notes |
|---|---|---|
| escalation_id | BIGINT PK AUTO_INCREMENT | |
| conversation_id | VARCHAR(50) | FK, CASCADE |
| order_id | VARCHAR(50) NULL | denormalized copy for fast dashboard queries without a join |
| reason | VARCHAR(255) | |
| status | VARCHAR(20) | PENDING / RESOLVED |
| assigned_to | VARCHAR(100) NULL | |
| created_at / resolved_at | TIMESTAMP | |

## Table: `ai_faq_knowledge_base`
| Column | Type | Notes |
|---|---|---|
| faq_id | INT PK AUTO_INCREMENT | |
| category | VARCHAR(50) | e.g. DELIVERY, PAYMENT, CANCELLATION |
| question | VARCHAR(255) | |
| answer | TEXT | ground-truth answer text, returned verbatim by `search_faq` |
| is_active | BOOLEAN | inactive rows excluded from search without deleting history |

## Indexing Rationale
- `idx_conv_order` / `idx_conv_mobile` — the two lookup patterns the
  identity-check step needs on every message.
- `idx_msg_conversation` — history endpoint and context-window loader
  both filter by conversation_id, ordered by created_at (PK order is
  sufficient since message_id is monotonic and matches insert order).
- `idx_esc_conversation` — resolve endpoint and escalations dashboard
  feed both filter by this.

## Why New Tables Here (vs. reusing existing ones)
Per the "reuse before creating" rule: `order_audit_trail` was
considered and rejected for storing chat messages — it's a
single-event-per-row state-transition log tied 1:1 to `event_type`
enum values from `AuditEventType`, semantically different from a
multi-turn conversational transcript, and overloading it would break
its existing contract (used by `GET /api/v1/orders/{id}/audit`).
Similarly, `inventory_alerts` was considered for escalations and
rejected — it's schema-shaped specifically for stock alerts
(`item_id`, `threshold_value`), not a good fit for chat escalations.
New tables here are a genuine, justified gap, not a shortcut.

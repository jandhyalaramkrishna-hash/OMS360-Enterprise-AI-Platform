# SQL Validation — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## 1. Row-level correctness after a conversation
```sql
-- Every message for a conversation should be present, in the right order
SELECT message_id, sender, tool_called, guard_triggered, created_at
FROM ai_chatbot_messages
WHERE conversation_id = 'CONV-88213'
ORDER BY message_id ASC;
```

## 2. Referential integrity — no orphan messages
```sql
-- Should return 0 rows
SELECT m.message_id
FROM ai_chatbot_messages m
LEFT JOIN ai_chatbot_conversations c ON m.conversation_id = c.conversation_id
WHERE c.conversation_id IS NULL;
```

## 3. Referential integrity — no orphan escalations
```sql
-- Should return 0 rows
SELECT e.escalation_id
FROM ai_chatbot_escalations e
LEFT JOIN ai_chatbot_conversations c ON e.conversation_id = c.conversation_id
WHERE c.conversation_id IS NULL;
```

## 4. order_id FK behaves as SET NULL, not CASCADE
```sql
-- Setup: pick a conversation tied to an order, then (in a disposable
-- test DB only) delete the order and confirm the conversation SURVIVES
-- with order_id now NULL, unlike kitchen_status/delivery_status which
-- would cascade-delete.
SELECT conversation_id, order_id FROM ai_chatbot_conversations
WHERE conversation_id = 'CONV-88213';
-- (delete the test order in a sandboxed test DB)
SELECT conversation_id, order_id FROM ai_chatbot_conversations
WHERE conversation_id = 'CONV-88213';
-- Expect: row still exists, order_id is now NULL
```

## 5. No cross-customer data leakage in stored messages
```sql
-- For every message that mentions an order_id in its text, the
-- conversation's customer_mobile must match that order's mobile.
-- (Run as a manual/automated audit query, not a live constraint —
-- catches any bug where the identity guard was bypassed.)
SELECT c.conversation_id, c.customer_mobile, c.order_id, o.mobile AS order_owner_mobile
FROM ai_chatbot_conversations c
JOIN orders_master o ON c.order_id = o.order_id
WHERE c.customer_mobile <> o.mobile
  AND c.customer_mobile <> o.mobile_number;
-- Expect: 0 rows. Any row here is a Sev-1 data-leakage defect.
```

## 6. Guard-trigger rate (AI quality signal, not a pass/fail gate)
```sql
SELECT
  COUNT(*) AS total_ai_replies,
  SUM(guard_triggered) AS guard_triggered_count,
  ROUND(SUM(guard_triggered) / COUNT(*) * 100, 2) AS guard_trigger_pct
FROM ai_chatbot_messages
WHERE sender = 'AI';
-- Use to track trend over time in staging/prod; a sudden spike signals
-- a prompt regression or provider behavior change worth investigating.
```

## 7. Escalation SLA check
```sql
-- Escalations open longer than 24 hours with no resolution
SELECT escalation_id, conversation_id, reason, created_at
FROM ai_chatbot_escalations
WHERE status = 'PENDING'
  AND created_at < NOW() - INTERVAL 24 HOUR;
```

## 8. FAQ table sanity
```sql
-- No duplicate active questions in the same category
SELECT category, question, COUNT(*) AS cnt
FROM ai_faq_knowledge_base
WHERE is_active = TRUE
GROUP BY category, question
HAVING COUNT(*) > 1;
-- Expect: 0 rows
```

## 9. Regression proof — existing tables untouched
```sql
-- Row counts / schema of existing core tables before vs after this
-- feature's migration should be identical in structure (compare
-- DESCRIBE output pre/post-migration; row counts unaffected since
-- migration 004 does not INSERT/UPDATE/DELETE any existing table).
DESCRIBE orders_master;
DESCRIBE order_items;
DESCRIBE kitchen_status;
DESCRIBE delivery_status;
-- Expect: byte-for-byte identical to pre-migration schema dump.
```

# Performance Testing — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1

## 1. Latency Budgets
| Component | Target (p95) | Notes |
|---|---|---|
| Identity check + history load (DB only) | < 100 ms | Simple indexed queries |
| LLM call (no tool) | < 1.5 s | FAQ-only answer |
| LLM call (1 tool round-trip) | < 3 s | Most common case (order status/ETA) |
| Total API response time | < 3.5 s | End-to-end, matches `HTTP_CLIENT_TIMEOUT_SECONDS`-style existing timeout philosophy |
| Fallback on provider timeout | ≤ configured timeout + 200ms | Must never hang the customer |

## 2. Load Test Scenarios
| Scenario | Setup | Pass Criteria |
|---|---|---|
| Concurrent conversations | 100 simultaneous distinct conversation_ids, 1 msg/sec each | p95 latency within budget, 0 cross-conversation data mixing |
| Sustained order-status queries | 500 requests/min for 10 min, mock provider | No memory leak, no connection pool exhaustion on the DB side |
| Rate-limit correctness under load | 1 mobile number sending 100 req/min | 429 returned consistently after threshold, no false positives for other mobiles |
| Mixed flag states | 50% of instances flag ON, 50% OFF (rolling deploy simulation) | No crash, no shared-state corruption |
| DB growth | Simulate 10,000 conversations / 60,000 messages | Query plans for history/identity-check remain index-backed (EXPLAIN shows index usage, not full table scan) |

## 3. Cost Control Validation (LLM-specific "performance" concern)
- Verify conversation-summary compression actually triggers at the
  documented 6-turn threshold (Feature-01 doc, Section 9) — without it,
  token cost grows unbounded per long conversation.
- Verify system prompt + tool schema token count stays within the
  documented ~700 token estimate (system prompt + tools) — regression
  test this if the prompt is ever edited, since prompt bloat directly
  increases per-message cost and latency.
- Verify the 1000-character input cap is enforced server-side, not
  just documented (prevents a single oversized message from blowing
  the context budget).

## 4. Degradation Behavior Under Provider Slowness
| Provider latency | Expected system behavior |
|---|---|
| Normal (<3s) | Normal reply |
| Slow (3–8s) | Reply still returned, but should be flagged in logs for SRE visibility (approaching timeout) |
| Timeout (>configured limit) | Graceful fallback reply, logged as a failure, does not retry indefinitely |
| Provider fully down | Circuit breaker (recommended pattern) trips after N consecutive failures, short-circuits to fallback immediately for a cooldown window instead of waiting out the timeout on every request — protects overall API latency during an outage |

## 5. Non-Functional Pass Criteria for Sign-off
- p95 total response time within budget under the 100-concurrent-conversation load test
- Rate limiting has 0 false positives/negatives in the dedicated test
- No degradation to `POST /api/v1/orders` latency when chatbot is under load (proves resource isolation — recommend a separate connection pool or async execution for the chatbot's DB/LLM calls so it can't starve the order-creation path)

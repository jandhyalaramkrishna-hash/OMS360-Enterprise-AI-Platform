# Business Requirements Document (BRD) — AI Customer Support Chatbot
OMS360 AI Enterprise v1.1 | Related: docs/architecture/Feature-01-AI-Customer-Support-Chatbot_v1.1.md

## BR-1. Problem Statement
Support volume for repetitive order-status/refund/cancellation
questions has no self-service deflection today. Every question — no
matter how simple — consumes a human agent's time and has response
latency bounded by agent availability.

## BR-2. Business Objectives
| ID | Objective | Success Metric |
|---|---|---|
| BR-2.1 | Deflect repetitive status/ETA/refund questions from human agents | ≥ 40% of chatbot conversations resolved without escalation |
| BR-2.2 | Provide 24/7 answer availability | Chatbot uptime independent of agent shift hours |
| BR-2.3 | Never give a customer an incorrect order fact | 0 confirmed hallucinated-fact incidents in production |
| BR-2.4 | Escalate genuinely hard cases to a human with full context | 100% of escalations carry conversation_id + order_id + reason to the agent |
| BR-2.5 | Zero impact on existing order fulfillment flow if AI misbehaves | Feature flag off = zero behavioral change to `order_service`/`consumer.py` |

## BR-3. In Scope
- Order status, delivery ETA, cancellation eligibility, refund status Q&A
- General FAQ answering from a controlled knowledge base
- Escalation to human agents via the existing Operations dashboard pattern
- Conversation logging for QA review and support-quality auditing

## BR-4. Out of Scope (this version)
- The bot cannot cancel, refund, or modify any order (read-only, always)
- No voice channel (text/chat only)
- No multi-language guarantee (best-effort only, documented limitation)
- No fine-tuning of a custom model — uses a general-purpose LLM via
  the existing `AI_PROVIDER` configuration with tool-calling
- Not a replacement for the existing Operations dashboard alerts —
  it's a new, additional escalation source feeding the same dashboard

## BR-5. Stakeholders
| Stakeholder | Interest |
|---|---|
| Customer | Fast, accurate self-service answers |
| Support/Ops team | Fewer repetitive tickets, better-contextualized escalations |
| Engineering/SRE | Feature must be toggleable, observable, and non-blocking to core flow |
| QA | Feature must be independently testable, including negative/hallucination testing |
| Compliance | No PII leakage across customers; conversation data retention policy required |

## BR-6. Dependencies
- Requires `orders_master`, `order_audit_trail`, `delivery_status`,
  `kitchen_status`, `transactions` (all existing, read-only access)
- Requires an LLM provider credential configured in `AI_API_KEY`
  (currently blank — must be provisioned before `ai_chatbot_enabled`
  can be turned on in any real environment)
- Requires `ai_features_enabled` = true AND a new `ai_chatbot_enabled`
  sub-flag = true (both default false — opt-in only)

## BR-7. Assumptions
- The actual customer-facing chat UI lives in an external customer
  app not present in this repository; this repo delivers the API and
  a demo widget only.
- No authentication system exists yet, so identity verification for
  this feature is done via mobile-number-matches-order-record, the
  same weak-identity model the rest of the existing system uses
  (documented limitation, not a new gap introduced by this feature).

## BR-8. Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM provider cost overrun at scale | Medium | Medium | Rate limiting, conversation-summary compression, response length cap |
| Hallucinated order fact reaches a customer | Low (with guard) | High | Post-generation guard (Section 11/12 of Feature-01 doc) |
| PII sent to a third-party LLM provider | Medium | High | Only order_id/status enums sent, never full address/card data |
| Agents ignore AI escalations (alert fatigue) | Medium | Medium | Escalations reuse the existing, already-trusted Alerts panel pattern rather than a new siloed inbox |

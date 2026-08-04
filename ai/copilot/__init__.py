"""
AI Copilot - OMS-360 Enterprise Food Delivery Platform
"AI Copilot Sprint 1" (Phase 1: AI Copilot menu, AI Chat interface,
Business Question & Answer, Executive Summary, Business Insights)

Governance note: the numbered "Sprint 1-9" AI-platform line closed at
v1.0.0 (see docs/governance/DECISION-LOG.md DEC-0022) with an explicit
note that future AI work would begin a new, separately-scoped version.
This package is that new line - tracked from DEC-0033 onward, starting
fresh at "AI Copilot Sprint 1" rather than continuing the old Sprint
1-9 numbering.

Hybrid architecture (per explicit Product Owner instruction): business
facts (pending orders, failed orders, inventory, kitchen, delivery,
sales, monitoring) are ALWAYS answered from the real OMS360 MySQL
database via deterministic intent matching and direct, parameterized
SQLAlchemy queries - never fabricated, never routed through an LLM.
An LLM (selected automatically via ai.copilot.provider_manager's AUTO
chain: OpenAI -> Anthropic -> Ollama -> Azure OpenAI -> none configured)
is reserved for reasoning/language tasks layered on top of that same
real data in later phases (Explain SQL, Root Cause Analysis, QA test
generation, documentation, interview coaching, etc.) - never for
generating the business numbers themselves. If no LLM provider is
configured, Business Q&A, Executive Summary, and Business Insights all
still work completely via the deterministic engine alone.

Modules:
  provider_manager.py        - AIProviderManager: AUTO-selects a real,
                                configured LLM provider, or reports none
                                configured (deterministic-only mode).
  intents.py                 - BUSINESS_INTENTS catalog: one entry per
                                supported business question, each with
                                its own real SQL query, display SQL
                                text, related tables, and business-flow
                                explanation - plus classify_question(),
                                a deterministic keyword matcher.
  business_qa_service.py     - BusinessQAService.ask(): matches a
                                question to an intent and runs its real
                                query; never displays SQL automatically
                                (per explicit UI requirement) - View
                                SQL/Explain SQL/Related Tables/Business
                                Flow are fetched lazily, only on request.
  executive_summary_service.py - Composes real KPI queries (reusing
                                app.routes.dashboard's existing
                                kpi_bar()/analytics_summary() functions
                                directly, not duplicating their query
                                logic) into a short templated paragraph.
  business_insights_service.py - A handful of rule-based observations
                                over real data (low stock, cancellation
                                rate, kitchen backlog, etc.).
"""

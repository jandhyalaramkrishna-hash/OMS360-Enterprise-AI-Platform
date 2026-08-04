"""
AI Copilot - Request / Response Models
OMS-360 Enterprise Food Delivery Platform

AI Copilot Sprint 1 (Phase 1). New line, DEC-0033 onward - see
ai/copilot/__init__.py for why this is not a continuation of the closed
Sprint 1-9 AI Runtime numbering.

Mirrors app/api/ai/schemas.py's own conventions (pydantic BaseModel
response models, ErrorResponse re-exported for Swagger's `responses=`
blocks) rather than introducing a second style. One deliberate
difference from that file: CopilotAskRequest is this package's first
actual JSON request body model, since POST /copilot/ask is this
package's first non-GET endpoint.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas import ErrorResponse  # noqa: F401  (re-exported for responses= blocks)


# --- Request Models ----------------------------------------------------------

class CopilotAskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="A plain-English business question, e.g. 'How many pending orders?'.")


class CopilotQAAssistantRequest(BaseModel):
    target: str = Field(..., min_length=1, description="The real endpoint being tested, e.g. 'POST /api/v1/orders'.")
    context: str = Field("", description="A short, factual description of what the endpoint does - the only source of business rules the generator may use.")
    test_types: List[str] = Field(
        default_factory=lambda: ["functional", "negative", "regression", "api", "sql"],
        description="Which test-case types to generate. Unknown values are ignored; an empty/invalid list falls back to all five.",
    )


class CopilotDocsAssistantRequest(BaseModel):
    doc_type: str = Field(..., min_length=1, description="'readme_section' | 'sprint_summary' | 'release_notes' | 'api_docs'.")
    facts: str = Field(..., min_length=1, description="Real, caller-supplied facts/bullet points to turn into prose. The generator never invents facts not present here.")
    title: str = Field("", description="Optional document title/heading override.")


class CopilotLearningAskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="A free-form question about how OMS-360 works - matched to the nearest known learning topic.")


# --- Response Models ----------------------------------------------------------

class CopilotAskResponse(BaseModel):
    question: str
    matched: bool = Field(..., description="True if the question matched a known business intent.")
    intent: Optional[str] = Field(None, description="The matched intent key, e.g. 'pending_orders'. Use this to fetch SQL/Explain/Related Tables/Business Flow. None if unmatched.")
    answer_text: str = Field(..., description="The business answer. Always grounded in real OMS-360 data - never fabricated.")
    value: Optional[object] = Field(None, description="The raw computed value behind answer_text (number/string), for a UI to format itself if desired.")
    reworded_by_ai: bool = Field(..., description="True if a configured LLM rephrased answer_text (numbers are guaranteed unchanged). False in deterministic-only mode.")
    active_provider: Optional[str] = Field(None, description="Name of the LLM provider that reworded the answer, if any (e.g. 'openai'). None if deterministic-only.")
    suggested_questions: List[str] = Field(default_factory=list, description="Example questions to try, populated only when matched=False.")


class CopilotIntentCatalogItem(BaseModel):
    key: str = Field(..., description="Stable intent key, e.g. 'pending_orders'. Use this (not the question text) to call the intent-keyed endpoints below.")
    question_example: str = Field(..., description="Human-readable label for this catalog entry - shown in the Business Question / SQL Query dropdowns.")


class CopilotIntentCatalogResponse(BaseModel):
    intents: List[CopilotIntentCatalogItem] = Field(..., description="Every supported business query, in a fixed order - powers the Business Question and SQL Query dropdowns.")


class CopilotIntentAnswerResponse(BaseModel):
    intent: str
    question: str = Field(..., description="The catalog's canonical question text for this intent.")
    answer_text: str = Field(..., description="The business answer. Always grounded in real OMS-360 data - never fabricated.")
    value: Optional[object] = Field(None, description="The raw computed value behind answer_text (number/string/list), for a UI to format itself if desired.")
    reworded_by_ai: bool = Field(..., description="True if a configured LLM rephrased answer_text (numbers are guaranteed unchanged). False in deterministic-only mode.")
    active_provider: Optional[str] = Field(None, description="Name of the LLM provider that reworded the answer, if any. None if deterministic-only.")


class CopilotSqlResponse(BaseModel):
    intent: str
    sql_text: str = Field(..., description="A literal, parameter-free description of the query shape actually executed - never shown automatically, fetched only on explicit 'View SQL'.")


class CopilotExplainResponse(BaseModel):
    intent: str
    explanation: str = Field(..., description="A plain-English explanation of the query and the business flow it belongs to.")


class CopilotRelatedTablesResponse(BaseModel):
    intent: str
    related_tables: List[str]


class CopilotBusinessFlowResponse(BaseModel):
    intent: str
    business_flow: str


class CopilotExecutiveSummaryResponse(BaseModel):
    summary_text: str = Field(..., description="A short paragraph composed from real KPI/analytics numbers - never LLM-generated.")
    kpis: dict = Field(..., description="The raw kpi_bar()/analytics_summary() data the summary_text was built from.")


class CopilotInsight(BaseModel):
    severity: str = Field(..., description="'info' | 'warning' | 'critical'.")
    message: str


class CopilotBusinessInsightsResponse(BaseModel):
    insights: List[CopilotInsight]


class CopilotProviderStatusResponse(BaseModel):
    active_provider: Optional[str] = Field(None, description="Currently active real LLM provider name, or None if running in deterministic-only mode.")
    source: str = Field(..., description="'explicit' | 'auto' | 'none_configured'.")
    reasoning_available: bool = Field(..., description="True if a real LLM is available for rewording/explanations. Business Q&A works either way.")
    checked_providers: List[str] = Field(..., description="Providers checked, in AUTO preference order.")
    copilot_enabled: bool = Field(..., description="Whether AI Copilot itself is enabled (COPILOT_ENABLED). Independent of ai_enabled/reasoning_available.")


class CopilotSupportedQuestionsResponse(BaseModel):
    questions: List[str]


# --- AI Copilot Sprint 2 additions --------------------------------------------

class CopilotReasonGroup(BaseModel):
    reason: str
    count: int
    most_recent_order_id: Optional[str] = None
    most_recent_transaction_id: Optional[str] = None
    most_recent_at: Optional[str] = None


class CopilotDuplicateExample(BaseModel):
    order_id: str
    transaction_id: str
    detected_at: Optional[str] = None
    outcome: str = Field(..., description="What happened to the original order for this transaction_id, correlated against orders_master/failed_orders.")


class CopilotRootCauseResponse(BaseModel):
    total_count: int = Field(..., description="Total real row count behind this analysis (failed_orders or duplicate_orders).")
    top_reasons: List[CopilotReasonGroup] = Field(default_factory=list, description="Grouped failure reasons with counts and a most-recent example each. Populated only for failed-orders analysis.")
    examples: List[CopilotDuplicateExample] = Field(default_factory=list, description="Recent duplicate-order examples, correlated back to orders_master/failed_orders. Populated only for duplicate-orders analysis.")
    explanation_text: str = Field(..., description="A natural-language root-cause explanation, always grounded in the real counts/reasons above.")
    investigation_steps: List[str] = Field(default_factory=list, description="Suggested next steps for investigating the issue.")
    ai_generated: bool = Field(..., description="True if a configured LLM elaborated on the real data above. False in deterministic-only mode.")


class CopilotQAAssistantResponse(BaseModel):
    target: str
    test_types: List[str]
    generated_text: str = Field(..., description="The generated test-case text, grounded in target/context only.")
    ai_generated: bool = Field(..., description="True if a configured LLM generated this text. False in deterministic-template mode.")


class CopilotDocsAssistantResponse(BaseModel):
    doc_type: str
    title: str
    generated_text: str = Field(..., description="The generated documentation text, grounded in the caller-supplied facts only.")
    ai_generated: bool = Field(..., description="True if a configured LLM generated this text. False in deterministic-template mode.")


class CopilotLearningTopic(BaseModel):
    topic: str
    title: str


class CopilotLearningTopicsResponse(BaseModel):
    topics: List[CopilotLearningTopic]


class CopilotLearningExplanationResponse(BaseModel):
    topic: str
    title: str
    text: str = Field(..., description="The topic's explanation - the hand-written knowledge-base text, optionally elaborated by a configured LLM (never invented beyond it).")
    ai_generated: bool = Field(..., description="True if a configured LLM elaborated on the hand-written text. False in deterministic mode.")


class CopilotLearningAskResponse(BaseModel):
    matched_topic: str
    title: str
    text: str
    ai_generated: bool

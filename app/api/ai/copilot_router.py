"""
AI Copilot - Routes
OMS-360 Enterprise Food Delivery Platform

AI Copilot Sprint 1 (Phase 1): AI Copilot menu, AI Chat interface,
Business Question & Answer, Executive Summary, Business Insights. New
line, DEC-0033 onward - see ai/copilot/__init__.py for why this is not a
continuation of the closed Sprint 1-9 AI Runtime numbering (DEC-0022).

Every route here is gated by RuntimeConfiguration.copilot_enabled
(COPILOT_ENABLED env var, defaults True) - NOT by ai_enabled/
require_ai_enabled, since AI Copilot's Business Q&A/Executive Summary/
Business Insights are fully functional with zero LLM provider
configured (see ai/runtime/config.py's copilot_enabled docstring).

UI requirement (explicit, from the approved plan): SQL is never
returned by POST /copilot/ask. It, along with the Explain SQL/Related
Tables/Business Flow text, is only ever available via the four separate
GET /copilot/intents/{intent}/... endpoints below, fetched lazily by the
UI only when the user clicks the corresponding button.

Business facts always come from real OMS-360 data via
ai.copilot.business_qa_service.BusinessQAService (real SQLAlchemy
queries against orders_master/inventory/kitchen_status/etc.) - never
fabricated by a mock provider. See ai/copilot/README.md.
"""

from typing import List

from fastapi import APIRouter, Depends

from app.database import get_db
from sqlalchemy.orm import Session

from ai.copilot.business_insights_service import BusinessInsightsService
from ai.copilot.business_qa_service import BusinessQAService
from ai.copilot.documentation_assistant_service import DocumentationAssistantService
from ai.copilot.executive_summary_service import ExecutiveSummaryService
from ai.copilot.intents import list_intent_catalog, list_supported_questions
from ai.copilot.learning_assistant_service import LearningAssistantService
from ai.copilot.provider_manager import AIProviderManager
from ai.copilot.qa_assistant_service import QAAssistantService
from ai.copilot.root_cause_service import RootCauseAnalysisService
from ai.core.exceptions import AICopilotDisabledError
from ai.dependencies import (
    get_business_insights_service,
    get_business_qa_service,
    get_copilot_runtime_config,
    get_documentation_assistant_service,
    get_executive_summary_service,
    get_learning_assistant_service,
    get_provider_manager,
    get_qa_assistant_service,
    get_root_cause_service,
)
from ai.runtime.config import RuntimeConfiguration

from app.api.ai.copilot_schemas import (
    CopilotAskRequest,
    CopilotAskResponse,
    CopilotBusinessFlowResponse,
    CopilotBusinessInsightsResponse,
    CopilotDocsAssistantRequest,
    CopilotDocsAssistantResponse,
    CopilotDuplicateExample,
    CopilotExecutiveSummaryResponse,
    CopilotExplainResponse,
    CopilotInsight,
    CopilotIntentAnswerResponse,
    CopilotIntentCatalogItem,
    CopilotIntentCatalogResponse,
    CopilotLearningAskRequest,
    CopilotLearningAskResponse,
    CopilotLearningExplanationResponse,
    CopilotLearningTopic,
    CopilotLearningTopicsResponse,
    CopilotProviderStatusResponse,
    CopilotQAAssistantRequest,
    CopilotQAAssistantResponse,
    CopilotReasonGroup,
    CopilotRelatedTablesResponse,
    CopilotRootCauseResponse,
    CopilotSqlResponse,
    CopilotSupportedQuestionsResponse,
)
from app.schemas import ErrorResponse

router = APIRouter(prefix="/api/v1/ai/copilot", tags=["AI Copilot"])


def _require_copilot_enabled(runtime_config: RuntimeConfiguration = Depends(get_copilot_runtime_config)) -> None:
    if not runtime_config.copilot_enabled:
        raise AICopilotDisabledError()


@router.post(
    "/ask",
    response_model=CopilotAskResponse,
    summary="Ask a business question",
    description=(
        "Answers a plain-English business question (pending orders, failed "
        "orders, inventory, kitchen, delivery, sales, etc.) using a "
        "deterministic intent match against real OMS-360 data - never a "
        "fabricated number. If a real LLM provider is configured (AUTO: "
        "OpenAI -> Anthropic -> Ollama -> Azure OpenAI), it may rephrase "
        "the sentence but cannot change any number (see "
        "BusinessQAService._numbers_preserved). SQL is never included in "
        "this response - fetch it separately via GET "
        "/intents/{intent}/sql only if the user clicks 'View SQL'."
    ),
    responses={
        403: {"model": ErrorResponse, "description": "AI Copilot is disabled (COPILOT_ENABLED=false)."},
        422: {"model": ErrorResponse, "description": "question was missing or blank."},
    },
    dependencies=[Depends(_require_copilot_enabled)],
)
async def ask_business_question(
    body: CopilotAskRequest,
    db: Session = Depends(get_db),
    qa_service: BusinessQAService = Depends(get_business_qa_service),
) -> CopilotAskResponse:
    result = await qa_service.ask(body.question, db)
    return CopilotAskResponse(
        question=result.question,
        matched=result.matched,
        intent=result.intent,
        answer_text=result.answer_text,
        value=result.value,
        reworded_by_ai=result.reworded_by_ai,
        active_provider=result.active_provider,
        suggested_questions=list(result.suggested_questions),
    )


@router.get(
    "/questions",
    response_model=CopilotSupportedQuestionsResponse,
    summary="List example supported questions",
    description="The example question catalog (one per supported intent) - useful for a UI's suggestion chips.",
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_supported_questions() -> CopilotSupportedQuestionsResponse:
    return CopilotSupportedQuestionsResponse(questions=list_supported_questions())


@router.get(
    "/catalog",
    response_model=CopilotIntentCatalogResponse,
    summary="Full intent catalog (key + label)",
    description=(
        "Every supported business query as (key, question_example) pairs, in a "
        "fixed order. Powers the 'Business Question' and 'SQL Query' dropdowns: "
        "the UI selects by `key`, then calls GET /intents/{key}/answer (or "
        "/sql, /explain, /related-tables, /business-flow) directly - no free-text "
        "matching involved, since the caller already picked an exact catalog entry."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_intent_catalog() -> CopilotIntentCatalogResponse:
    return CopilotIntentCatalogResponse(intents=[CopilotIntentCatalogItem(**item) for item in list_intent_catalog()])


@router.get(
    "/intents/{intent}/answer",
    response_model=CopilotIntentAnswerResponse,
    summary="Answer a known intent directly (dropdown selection)",
    description=(
        "Computes the real answer for a KNOWN intent key, bypassing the "
        "free-text keyword matcher entirely - used by the 'Business Question' "
        "dropdown, where the caller already selected an exact catalog entry "
        "(see GET /catalog) rather than typing a question. Same deterministic "
        "guarantee as POST /ask: the number always comes from a real query; an "
        "LLM, if configured, may only rephrase the sentence."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown intent key."}},
    dependencies=[Depends(_require_copilot_enabled)],
)
async def get_intent_answer(
    intent: str,
    db: Session = Depends(get_db),
    qa_service: BusinessQAService = Depends(get_business_qa_service),
) -> CopilotIntentAnswerResponse:
    result = await qa_service.answer_intent(intent, db)
    return CopilotIntentAnswerResponse(
        intent=result.intent,
        question=result.question,
        answer_text=result.answer_text,
        value=result.value,
        reworded_by_ai=result.reworded_by_ai,
        active_provider=result.active_provider,
    )


@router.get(
    "/intents/{intent}/sql",
    response_model=CopilotSqlResponse,
    summary="View SQL for a matched intent",
    description="The literal query shape behind an intent - fetched only when the user explicitly clicks 'View SQL'. Never returned automatically by /ask.",
    responses={404: {"model": ErrorResponse, "description": "Unknown intent key."}},
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_intent_sql(intent: str, qa_service: BusinessQAService = Depends(get_business_qa_service)) -> CopilotSqlResponse:
    return CopilotSqlResponse(intent=intent, sql_text=qa_service.get_sql(intent))


@router.get(
    "/intents/{intent}/explain",
    response_model=CopilotExplainResponse,
    summary="Explain SQL for a matched intent",
    description=(
        "A plain-English explanation of the query and its business context. "
        "With use_ai=true (default) and a real LLM provider configured, the "
        "explanation is enriched by the LLM - strictly grounded in the "
        "intent's own sql_text/related_tables/business_flow facts, never "
        "inventing new ones. Falls back to the deterministic template if "
        "use_ai=false, no provider is configured, or the provider call "
        "fails for any reason."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown intent key."}},
    dependencies=[Depends(_require_copilot_enabled)],
)
async def get_intent_explanation(
    intent: str,
    use_ai: bool = True,
    qa_service: BusinessQAService = Depends(get_business_qa_service),
) -> CopilotExplainResponse:
    explanation = await qa_service.get_explanation_async(intent, use_ai=use_ai)
    return CopilotExplainResponse(intent=intent, explanation=explanation)


@router.get(
    "/intents/{intent}/related-tables",
    response_model=CopilotRelatedTablesResponse,
    summary="Related tables for a matched intent",
    responses={404: {"model": ErrorResponse, "description": "Unknown intent key."}},
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_intent_related_tables(intent: str, qa_service: BusinessQAService = Depends(get_business_qa_service)) -> CopilotRelatedTablesResponse:
    return CopilotRelatedTablesResponse(intent=intent, related_tables=qa_service.get_related_tables(intent))


@router.get(
    "/intents/{intent}/business-flow",
    response_model=CopilotBusinessFlowResponse,
    summary="Business flow explanation for a matched intent",
    responses={404: {"model": ErrorResponse, "description": "Unknown intent key."}},
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_intent_business_flow(intent: str, qa_service: BusinessQAService = Depends(get_business_qa_service)) -> CopilotBusinessFlowResponse:
    return CopilotBusinessFlowResponse(intent=intent, business_flow=qa_service.get_business_flow(intent))


@router.get(
    "/executive-summary",
    response_model=CopilotExecutiveSummaryResponse,
    summary="Executive summary",
    description="A short paragraph composed from real, live KPI/analytics numbers (reuses app/routes/dashboard.py's kpi_bar()/analytics_summary() directly) - never LLM-generated, since these are business facts, not a reasoning task.",
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_executive_summary(
    db: Session = Depends(get_db),
    summary_service: ExecutiveSummaryService = Depends(get_executive_summary_service),
) -> CopilotExecutiveSummaryResponse:
    summary = summary_service.build(db)
    return CopilotExecutiveSummaryResponse(summary_text=summary.summary_text, kpis=summary.kpis)


@router.get(
    "/business-insights",
    response_model=CopilotBusinessInsightsResponse,
    summary="Business insights",
    description="A handful of rule-based observations (cancellation rate, failed payments, out-of-stock/low-stock, kitchen backlog, pending backlog) over real, live data - explainable thresholds, not a black-box LLM judgment.",
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_business_insights(
    db: Session = Depends(get_db),
    insights_service: BusinessInsightsService = Depends(get_business_insights_service),
) -> CopilotBusinessInsightsResponse:
    insights: List = insights_service.build(db)
    return CopilotBusinessInsightsResponse(
        insights=[CopilotInsight(severity=i.severity, message=i.message) for i in insights]
    )


@router.get(
    "/provider-status",
    response_model=CopilotProviderStatusResponse,
    summary="AI Copilot provider status",
    description=(
        "Which real LLM provider (if any) is currently active for rewording/"
        "explanations, via the AUTO chain (OpenAI -> Anthropic -> Ollama -> "
        "Azure OpenAI -> deterministic-only). Business Q&A itself always "
        "works regardless of this status - it only affects whether answers "
        "are rephrased and whether LLM-backed reasoning features (future "
        "phases) are available."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
def get_provider_status(
    provider_manager: AIProviderManager = Depends(get_provider_manager),
    runtime_config: RuntimeConfiguration = Depends(get_copilot_runtime_config),
) -> CopilotProviderStatusResponse:
    status = provider_manager.status()
    return CopilotProviderStatusResponse(
        active_provider=status["active_provider"],
        source=status["source"],
        reasoning_available=status["reasoning_available"],
        checked_providers=status["checked_providers"],
        copilot_enabled=runtime_config.copilot_enabled,
    )


# --- AI Root Cause Analysis (AI Copilot Sprint 2) ---------------------------

@router.get(
    "/root-cause/failed-orders",
    response_model=CopilotRootCauseResponse,
    summary="Root cause analysis - failed orders",
    description=(
        "Groups the real failed_orders table by reason (count + most recent "
        "example per reason) and returns a natural-language root-cause "
        "explanation plus suggested investigation steps. If a real LLM "
        "provider is configured, it elaborates on the exact computed "
        "counts/reasons given to it - it never invents a failure reason or "
        "count. Zero failed orders is a valid, non-error outcome."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
async def get_root_cause_failed_orders(
    db: Session = Depends(get_db),
    root_cause_service: RootCauseAnalysisService = Depends(get_root_cause_service),
) -> CopilotRootCauseResponse:
    result = await root_cause_service.analyze_failed_orders(db)
    return CopilotRootCauseResponse(
        total_count=result.total_count,
        top_reasons=[CopilotReasonGroup(**g.__dict__) for g in result.top_reasons],
        examples=[],
        explanation_text=result.explanation_text,
        investigation_steps=result.investigation_steps,
        ai_generated=result.ai_generated,
    )


@router.get(
    "/root-cause/duplicate-orders",
    response_model=CopilotRootCauseResponse,
    summary="Root cause analysis - duplicate orders",
    description=(
        "Analyzes the real duplicate_orders table, correlating each "
        "duplicate's transaction_id back to orders_master/failed_orders to "
        "describe what happened to the original order, and returns a "
        "natural-language root-cause explanation plus suggested "
        "investigation steps. If a real LLM provider is configured, it "
        "elaborates on the exact computed examples given to it. Zero "
        "duplicate orders is a valid, non-error outcome."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
async def get_root_cause_duplicate_orders(
    db: Session = Depends(get_db),
    root_cause_service: RootCauseAnalysisService = Depends(get_root_cause_service),
) -> CopilotRootCauseResponse:
    result = await root_cause_service.analyze_duplicate_orders(db)
    return CopilotRootCauseResponse(
        total_count=result.total_count,
        top_reasons=[],
        examples=[CopilotDuplicateExample(**e) for e in result.examples],
        explanation_text=result.explanation_text,
        investigation_steps=result.investigation_steps,
        ai_generated=result.ai_generated,
    )


# --- AI QA Assistant (AI Copilot Sprint 2) ----------------------------------

@router.post(
    "/qa-assistant/generate",
    response_model=CopilotQAAssistantResponse,
    summary="Generate test cases for a real endpoint",
    description=(
        "Generates functional/negative/regression/API/SQL-validation test "
        "cases for a real endpoint (`target`), grounded strictly in the "
        "caller-supplied `context` describing what it does. If a real LLM "
        "provider is configured, it writes the test cases; it is "
        "explicitly instructed not to invent business rules beyond what "
        "`context` states. If no provider is configured, a deterministic "
        "checklist-style template is generated instead."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
async def generate_qa_test_cases(
    body: CopilotQAAssistantRequest,
    qa_assistant_service: QAAssistantService = Depends(get_qa_assistant_service),
) -> CopilotQAAssistantResponse:
    result = await qa_assistant_service.generate(body.target, body.context, body.test_types)
    return CopilotQAAssistantResponse(
        target=result.target,
        test_types=list(result.test_types),
        generated_text=result.generated_text,
        ai_generated=result.ai_generated,
    )


# --- AI Documentation Assistant (AI Copilot Sprint 2) -----------------------

@router.post(
    "/docs-assistant/generate",
    response_model=CopilotDocsAssistantResponse,
    summary="Generate documentation prose from real facts",
    description=(
        "Turns a caller-supplied block of real facts (`facts`) into a "
        "structured section matching `doc_type` (readme_section | "
        "sprint_summary | release_notes | api_docs). Never invents a fact "
        "not present in `facts` - an LLM, if configured, only organizes/"
        "formats/expands the phrasing around them. If no provider is "
        "configured, a deterministic template is used instead."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
async def generate_documentation(
    body: CopilotDocsAssistantRequest,
    docs_assistant_service: DocumentationAssistantService = Depends(get_documentation_assistant_service),
) -> CopilotDocsAssistantResponse:
    result = await docs_assistant_service.generate(body.doc_type, body.facts, body.title)
    return CopilotDocsAssistantResponse(
        doc_type=result.doc_type,
        title=result.title,
        generated_text=result.generated_text,
        ai_generated=result.ai_generated,
    )


# --- AI Learning Assistant (AI Copilot Sprint 2) ----------------------------

@router.get(
    "/learning/topics",
    response_model=CopilotLearningTopicsResponse,
    summary="List learning topics",
    description="The hand-written knowledge-base topics available (architecture, kafka, inventory, kitchen, delivery, monitoring, database).",
    dependencies=[Depends(_require_copilot_enabled)],
)
def list_learning_topics(
    learning_service: LearningAssistantService = Depends(get_learning_assistant_service),
) -> CopilotLearningTopicsResponse:
    topics = learning_service.list_topics()
    return CopilotLearningTopicsResponse(topics=[CopilotLearningTopic(**t) for t in topics])


@router.get(
    "/learning/topics/{topic}",
    response_model=CopilotLearningExplanationResponse,
    summary="Explain a learning topic",
    description=(
        "Returns the hand-written, factually-grounded explanation for one "
        "topic. If a real LLM provider is configured, it may elaborate/"
        "rephrase that same text (never invent beyond it)."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown topic."}},
    dependencies=[Depends(_require_copilot_enabled)],
)
async def explain_learning_topic(
    topic: str,
    use_ai: bool = True,
    learning_service: LearningAssistantService = Depends(get_learning_assistant_service),
) -> CopilotLearningExplanationResponse:
    answer = await learning_service.explain_topic(topic, use_ai=use_ai)
    return CopilotLearningExplanationResponse(
        topic=answer.topic, title=answer.title, text=answer.text, ai_generated=answer.ai_generated
    )


@router.post(
    "/learning/ask",
    response_model=CopilotLearningAskResponse,
    summary="Ask a free-form learning question",
    description=(
        "Matches a free-form question to the nearest known learning topic "
        "via simple keyword matching, then returns that topic's "
        "explanation (optionally LLM-elaborated, never invented beyond "
        "it)."
    ),
    dependencies=[Depends(_require_copilot_enabled)],
)
async def ask_learning_question(
    body: CopilotLearningAskRequest,
    learning_service: LearningAssistantService = Depends(get_learning_assistant_service),
) -> CopilotLearningAskResponse:
    answer = await learning_service.ask(body.question)
    return CopilotLearningAskResponse(
        matched_topic=answer.topic, title=answer.title, text=answer.text, ai_generated=answer.ai_generated
    )

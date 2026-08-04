"""
AI Service Layer - Dependency injection providers
OMS-360 Enterprise Food Delivery Platform

FastAPI-style Depends(...) providers, mirroring how the existing OMS360
app exposes app/database.py's get_db(). These are not wired into any
route as of Sprint 2 - they exist so future AI routes/tests can use them
exactly like the rest of the app uses Depends(get_db).

Sprint 2 additions (get_ai_service, get_ai_health_service,
get_provider_registry, get_ai_metrics) are appended below the Sprint 1
providers, which are unchanged.
"""

import os

from app.core.logging_config import get_logger

from ai.agents.agent_service import AgentService
from ai.agents.factory import AgentFactory
from ai.agents.health import AgentHealthChecker
from ai.agents.messaging import AgentMessageBus
from ai.agents.orchestrator import AgentOrchestrator
from ai.config import get_ai_settings
from ai.copilot.business_qa_service import BusinessQAService
from ai.copilot.business_insights_service import BusinessInsightsService
from ai.copilot.executive_summary_service import ExecutiveSummaryService
from ai.copilot.provider_manager import AIProviderManager
from ai.copilot.root_cause_service import RootCauseAnalysisService
from ai.copilot.qa_assistant_service import QAAssistantService
from ai.copilot.documentation_assistant_service import DocumentationAssistantService
from ai.copilot.learning_assistant_service import LearningAssistantService
from ai.core.exceptions import AIFeatureDisabledError
from ai.evals.accuracy import AccuracyScorer
from ai.evals.evaluation_service import EvaluationService
from ai.evals.latency import LatencyAnalyzer
from ai.evals.mock_dataset import MockEvalDataset
from ai.evals.prompt_evaluator import PromptEvaluator
from ai.evals.reports import EvaluationReportBuilder
from ai.evals.runner import EvalRunner
from ai.integration.health import PlatformHealthChecker
from ai.integration.workflow_service import AIWorkflowService
from ai.mcp.config import MCPConfig, load_mcp_config
from ai.mcp.health import MCPHealthChecker
from ai.mcp.registry import MCPToolRegistry
from ai.mcp.router import MCPRequestRouter
from ai.mcp.server import MCPServer
from ai.mcp.tools.factory import MCPToolFactory
from ai.metrics import AIMetrics, get_ai_metrics as _get_ai_metrics
from ai.prompts.loader import PromptLoader
from ai.providers.health import ProviderHealthChecker
from ai.providers.registry import ProviderRegistry
from ai.rag.config import RAGConfig, load_rag_config
from ai.rag.context_builder import ContextBuilder
from ai.rag.document_loader import DocumentLoaderBase, MockDocumentLoader
from ai.rag.document_parser import DocumentParserBase, SimpleDocumentParser
from ai.rag.knowledge_base import KnowledgeBase
from ai.rag.mock_retriever import MockRetriever
from ai.rag.search_service import RAGSearchService
from ai.runtime.config import RuntimeConfiguration
from ai.runtime.loader import RuntimeConfigLoader, get_runtime_config_loader
from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService
from ai.services.factory import ServiceFactory
from ai.services.health_service import AIHealthService

logger = get_logger("ai.dependencies")

# Process-lifetime singletons - cheap, stateless-except-for-registrations,
# safe to share across requests (mirrors how app/config.py's `settings` is
# a module-level singleton).
_tool_registry = MCPToolRegistry()
_agent_orchestrator = AgentOrchestrator()
_eval_runner = EvalRunner()
_prompt_loader = PromptLoader()


def get_tool_registry() -> MCPToolRegistry:
    return _tool_registry


def get_agent_orchestrator() -> AgentOrchestrator:
    return _agent_orchestrator


def get_eval_runner() -> EvalRunner:
    return _eval_runner


def get_prompt_loader() -> PromptLoader:
    return _prompt_loader


def require_ai_enabled(capability: str = None):
    """Returns a FastAPI dependency callable that raises
    AIFeatureDisabledError unless the master flag - and, if `capability`
    is given, that capability's own granular flag - are both True.

    Usage (future, once wired into a route):
        @router.get("/rag/query", dependencies=[Depends(require_ai_enabled("rag_enabled"))])
    """

    def _check():
        ai_settings = get_ai_settings()
        if capability:
            if not ai_settings.is_capability_enabled(capability):
                logger.info("AI capability check failed", extra={"ctx_capability": capability})
                raise AIFeatureDisabledError(capability)
        elif not ai_settings.master_enabled:
            logger.info("AI master flag check failed")
            raise AIFeatureDisabledError()
        return ai_settings

    return _check


# --- Sprint 2 additions (AI Runtime Infrastructure) ------------------------
# Built via the pieces ServiceFactory composes, sharing ONE ProviderRegistry
# instance across AIService and AIHealthService (rather than calling
# ServiceFactory.build_ai_service()/build_health_service() independently,
# which would each build their own separate registry). Eager module-level
# singletons, matching the pattern used for the Sprint 1 providers above.

_provider_registry: ProviderRegistry = ServiceFactory.build_provider_registry()
_runtime_loader = get_runtime_config_loader()
_ai_service: AIService = AIService(_runtime_loader.load(), _runtime_loader.validation(), _provider_registry)
_ai_health_service: AIHealthService = AIHealthService(
    _runtime_loader.load(), _runtime_loader.validation(), _provider_registry
)


def get_provider_registry() -> ProviderRegistry:
    return _provider_registry


def get_ai_service() -> AIService:
    return _ai_service


def get_ai_health_service() -> AIHealthService:
    return _ai_health_service


def get_ai_metrics() -> AIMetrics:
    return _get_ai_metrics()


# --- Sprint 3 addition (AI API Layer) ---------------------------------------
# app/api/ai/router.py's GET /config and GET /features need the same
# RuntimeConfigLoader singleton already built above for _ai_service /
# _ai_health_service, exposed as its own Depends(...) provider rather than
# routes reaching into ai.runtime.loader.get_runtime_config_loader()
# directly - keeps every AI Runtime collaborator reachable through this one
# dependencies module, consistent with every other getter in this file.


def get_config_loader() -> RuntimeConfigLoader:
    return _runtime_loader


# --- Sprint 4 additions (AI Provider Framework: Mock Provider, Provider
# Factory, AI Chat Service, provider-level Health Check) -------------------
# Shares the SAME _provider_registry / _ai_service singletons built above
# for Sprint 2, rather than calling ServiceFactory.build_chat_service()
# (which would build its own, separate ProviderRegistry) - keeps exactly
# one provider registry as the source of truth for "which providers exist
# and are configured" across AIService, AIHealthService, and AIChatService
# alike. _provider_registry now includes "mock" (ai.providers.factory.
# ProviderFactory registers it alongside the four Sprint 2 adapters).

_provider_health_checker = ProviderHealthChecker()
_chat_service: AIChatService = AIChatService(
    _ai_service, _provider_registry, _provider_health_checker, _get_ai_metrics()
)


def get_provider_health_checker() -> ProviderHealthChecker:
    return _provider_health_checker


def get_chat_service() -> AIChatService:
    return _chat_service


# --- Sprint 5 additions (RAG Foundation: Knowledge Base, Document Loader/
# Parser, Mock Retriever, Context Builder, Search Service) -----------------
# Assembly (load -> parse -> retriever construction) happens once, here, at
# module import time - MockRetriever takes a pre-built list[ParsedChunk] via
# constructor injection (Dependency Inversion) rather than depending on
# KnowledgeBase/DocumentLoaderBase/DocumentParserBase itself, so this module
# is the one place that wires the RAG pipeline together. Reuses the SAME
# _ai_service singleton built above for Sprint 2 - RAGSearchService calls
# its existing require_capability("rag_enabled") gate rather than any new
# enablement mechanism (see ai/rag/search_service.py).

_rag_config: RAGConfig = load_rag_config()
_knowledge_base = KnowledgeBase()
_document_loader: DocumentLoaderBase = MockDocumentLoader()
_document_parser: DocumentParserBase = SimpleDocumentParser(chunk_max_chars=_rag_config.chunk_max_chars)

for _document in _document_loader.load():
    _knowledge_base.add_document(_document)

_chunks = []
for _document in _knowledge_base.all_documents():
    _chunks.extend(_document_parser.parse(_document))

_retriever = MockRetriever(_chunks)
_context_builder = ContextBuilder()
_search_service: RAGSearchService = RAGSearchService(_retriever, _context_builder, _ai_service, _rag_config)


def get_knowledge_base() -> KnowledgeBase:
    return _knowledge_base


def get_document_loader() -> DocumentLoaderBase:
    return _document_loader


def get_document_parser() -> DocumentParserBase:
    return _document_parser


def get_retriever() -> MockRetriever:
    return _retriever


def get_context_builder() -> ContextBuilder:
    return _context_builder


def get_rag_config() -> RAGConfig:
    return _rag_config


def get_search_service() -> RAGSearchService:
    return _search_service


# --- Sprint 6 additions (MCP Foundation: Server Framework, Request Router,
# Mock Tools, Health Check) -------------------------------------------------
# Registers the four Sprint 6 mock tools into the SAME _tool_registry
# singleton Sprint 1 already built above, rather than a second, MCP-server-
# only registry - the same "one shared registry" choice Sprint 4 made for
# providers (DEC-0017) and the pattern DEC-0018 (Sprint 5) generalized:
# reuse an existing collaborator instead of building a parallel one. Reuses
# the SAME _ai_service singleton built for Sprint 2 - MCPServer calls its
# existing require_capability("mcp_enabled") gate rather than any new
# enablement mechanism (see ai/mcp/server.py).

_mcp_config: MCPConfig = load_mcp_config()

for _tool in MCPToolFactory.create_all():
    _tool_registry.register(_tool)

_mcp_router: MCPRequestRouter = MCPRequestRouter(_tool_registry, _mcp_config)
_mcp_server: MCPServer = MCPServer(_mcp_router, _ai_service)
_mcp_health_checker = MCPHealthChecker()


def get_mcp_config() -> MCPConfig:
    return _mcp_config


def get_mcp_router() -> MCPRequestRouter:
    return _mcp_router


def get_mcp_server() -> MCPServer:
    return _mcp_server


def get_mcp_health_checker() -> MCPHealthChecker:
    return _mcp_health_checker


# --- Sprint 7 additions (Multi-Agent Foundation: Agent Registry, Factory,
# Mock Agents, Messaging, Health Check, Agent Service) ----------------------
# Registers the six Sprint 7 mock agents into the SAME _agent_orchestrator
# singleton Sprint 1 already built above, rather than a second orchestrator
# instance - the same "one shared collaborator" choice DEC-0017/0018/0019
# made for their respective registries. Reuses the SAME _ai_service
# singleton built for Sprint 2 - AgentService calls its existing
# require_capability("agents_enabled") gate rather than any new enablement
# mechanism (see ai/agents/agent_service.py).

_agent_message_bus: AgentMessageBus = AgentMessageBus()

for _agent in AgentFactory(_agent_message_bus).create_all():
    _agent_orchestrator.register(_agent)

_agent_health_checker = AgentHealthChecker()
_agent_service: AgentService = AgentService(_agent_orchestrator, _ai_service)


def get_agent_message_bus() -> AgentMessageBus:
    return _agent_message_bus


def get_agent_health_checker() -> AgentHealthChecker:
    return _agent_health_checker


def get_agent_service() -> AgentService:
    return _agent_service


# --- Sprint 8 additions (AI Evaluation Framework: Response Evaluation,
# Accuracy Scoring, Latency Metrics, Evaluation Reports, Mock Evaluation
# Dataset, Evaluation Service) -----------------------------------------------
# PromptEvaluator is built over the SAME _provider_registry singleton
# Sprint 2/4 already built above (via the "mock" provider registered by
# ProviderFactory) rather than constructing its own MockAIProvider - the
# same "one shared collaborator" choice DEC-0017/0018/0019/0020 made for
# their respective registries. EvaluationService reuses the SAME
# _eval_runner singleton Sprint 1 already built above, and the SAME
# _ai_service singleton built for Sprint 2 - it calls the existing
# require_capability("evals_enabled") gate rather than any new
# enablement mechanism (see ai/evals/evaluation_service.py).

_accuracy_scorer = AccuracyScorer()
_latency_analyzer = LatencyAnalyzer()
_evaluation_report_builder: EvaluationReportBuilder = EvaluationReportBuilder(_accuracy_scorer, _latency_analyzer)
_mock_eval_dataset = MockEvalDataset()
_prompt_evaluator: PromptEvaluator = PromptEvaluator(_provider_registry.get_provider("mock"), _eval_runner)
_evaluation_service: EvaluationService = EvaluationService(_eval_runner, _evaluation_report_builder, _ai_service)


def get_accuracy_scorer() -> AccuracyScorer:
    return _accuracy_scorer


def get_latency_analyzer() -> LatencyAnalyzer:
    return _latency_analyzer


def get_evaluation_report_builder() -> EvaluationReportBuilder:
    return _evaluation_report_builder


def get_mock_eval_dataset() -> MockEvalDataset:
    return _mock_eval_dataset


def get_prompt_evaluator() -> PromptEvaluator:
    return _prompt_evaluator


def get_evaluation_service() -> EvaluationService:
    return _evaluation_service


# --- Sprint 9 additions (Enterprise Integration: Unified AI Workflow,
# unified platform health check) ---------------------------------------------
# Both new collaborators are built from the SAME singletons already
# constructed above for Sprints 2-8 (_ai_service, _search_service,
# _mcp_server, _agent_service, _chat_service, _evaluation_service,
# _mock_eval_dataset for the workflow; _ai_health_service,
# _provider_health_checker/_provider_registry,
# _mcp_health_checker/_tool_registry,
# _agent_health_checker/_agent_orchestrator, and the shared AIMetrics
# singleton for platform health) - nothing here constructs a second
# instance of anything Sprint 2-8 already built. See DEC-0022.

_platform_health_checker: PlatformHealthChecker = PlatformHealthChecker(
    ai_health_service=_ai_health_service,
    provider_health_checker=_provider_health_checker,
    provider_registry=_provider_registry,
    mcp_health_checker=_mcp_health_checker,
    tool_registry=_tool_registry,
    agent_health_checker=_agent_health_checker,
    agent_orchestrator=_agent_orchestrator,
    ai_metrics=_get_ai_metrics(),
)

_ai_workflow_service: AIWorkflowService = AIWorkflowService(
    ai_service=_ai_service,
    search_service=_search_service,
    mcp_server=_mcp_server,
    agent_service=_agent_service,
    chat_service=_chat_service,
    evaluation_service=_evaluation_service,
    mock_eval_dataset=_mock_eval_dataset,
)


def get_platform_health_checker() -> PlatformHealthChecker:
    return _platform_health_checker


def get_ai_workflow_service() -> AIWorkflowService:
    return _ai_workflow_service


# --- AI Copilot additions (new line, DEC-0033 onward - see
# ai/copilot/__init__.py for why this is a fresh version rather than a
# continuation of the closed Sprint 1-9 numbering) --------------------------
# AIProviderManager shares the SAME _provider_registry singleton built
# above for Sprint 2/4 - the same "one shared collaborator" choice every
# prior sprint made for its own registry (DEC-0017 through DEC-0022) -
# rather than a second, copilot-only registry. An optional explicit
# override (AI_COPILOT_PROVIDER) is read once here; when unset, AUTO
# selection applies (see ai.copilot.provider_manager). BusinessQAService,
# ExecutiveSummaryService, and BusinessInsightsService read real data
# directly via an injected DB session per-request (app.database.get_db),
# not at module-import time like the Sprint 5 RAG pipeline - business
# data changes constantly, so nothing here is precomputed/cached.

_copilot_provider_manager: AIProviderManager = AIProviderManager(
    _provider_registry, explicit_provider_name=os.environ.get("AI_COPILOT_PROVIDER", "")
)
_business_qa_service: BusinessQAService = BusinessQAService(_copilot_provider_manager)
_executive_summary_service: ExecutiveSummaryService = ExecutiveSummaryService()
_business_insights_service: BusinessInsightsService = BusinessInsightsService()

# AI Copilot Sprint 2 additions (Root Cause Analysis, QA Assistant,
# Documentation Assistant, Learning Assistant) - every one of these
# reuses the SAME _copilot_provider_manager singleton built just above,
# rather than constructing a second AIProviderManager/ProviderRegistry -
# the same "one shared collaborator" choice every prior sprint made for
# its own registry (DEC-0017 through DEC-0022, applied again here for
# AI Copilot's own provider manager).
_root_cause_service: RootCauseAnalysisService = RootCauseAnalysisService(_copilot_provider_manager)
_qa_assistant_service: QAAssistantService = QAAssistantService(_copilot_provider_manager)
_documentation_assistant_service: DocumentationAssistantService = DocumentationAssistantService(_copilot_provider_manager)
_learning_assistant_service: LearningAssistantService = LearningAssistantService(_copilot_provider_manager)


def get_provider_manager() -> AIProviderManager:
    return _copilot_provider_manager


def get_business_qa_service() -> BusinessQAService:
    return _business_qa_service


def get_executive_summary_service() -> ExecutiveSummaryService:
    return _executive_summary_service


def get_business_insights_service() -> BusinessInsightsService:
    return _business_insights_service


def get_root_cause_service() -> RootCauseAnalysisService:
    return _root_cause_service


def get_qa_assistant_service() -> QAAssistantService:
    return _qa_assistant_service


def get_documentation_assistant_service() -> DocumentationAssistantService:
    return _documentation_assistant_service


def get_learning_assistant_service() -> LearningAssistantService:
    return _learning_assistant_service


def get_copilot_runtime_config() -> RuntimeConfiguration:
    """Returns the SAME RuntimeConfiguration snapshot _ai_service/
    _ai_health_service already loaded above (via _runtime_loader) - the
    copilot router reads .copilot_enabled from it directly, independent
    of ai_enabled (see RuntimeConfiguration.copilot_enabled)."""
    return _runtime_loader.load()

"""
AI Service Layer - Integration - Unified AI Workflow (Sprint 9)
OMS-360 Enterprise Food Delivery Platform

AIWorkflowService is the "Enterprise Integration" / "Unified AI Workflow"
deliverable: a single, sequential, end-to-end call chain over the five AI
modules built across Sprints 1-8, using ONLY already-built collaborators
via constructor injection (Dependency Inversion) - no new retrieval,
tool-call, agent-run, evaluation, or provider-call logic is implemented
here, and no new enablement/capability-gating mechanism is added. Each
step delegates entirely to its own module's existing, unmodified service,
so that service's own require_capability(...) gate (rag_enabled /
mcp_enabled / agents_enabled / evals_enabled, or the master ai_enabled
check inside AIChatService.send_message) applies exactly as it already
did when called standalone - see DEC-0022.

Flow, per run():
    1. RAGSearchService.search()      - retrieve FAQ context for the query
    2. MCPServer.call_tool()          - look up the mock order by order_id
    3. AgentService.run()             - the full six-agent mock lifecycle
    4. AIChatService.send_message()   - one completion call seeded with
                                         the retrieved RAG context
    5. EvaluationService.evaluate()   - scores the platform's built-in
                                         mock evaluation dataset through
                                         the SAME chat call path exercised
                                         in step 4, so the evaluation step
                                         is not a disconnected side-check
                                         but genuinely exercises the same
                                         provider call this workflow just
                                         made

A failure at any step (an unregistered tool, a disabled capability, an
agent execution error, ...) propagates as-is - this workflow does not
swallow, retry, or degrade errors from the modules it composes, matching
how every other Sprint 1-8 orchestrating service (AgentOrchestrator,
MCPRequestRouter, RAGSearchService) already behaves.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.core.logging_config import get_logger

from ai.agents.agent_service import AgentService
from ai.agents.base import AgentContext
from ai.core.exceptions import AIWorkflowInvalidRequestError
from ai.evals.evaluation_service import EvaluationService
from ai.evals.mock_dataset import MockEvalDataset
from ai.evals.reports import EvaluationSummary
from ai.mcp.models import ToolCallResult
from ai.mcp.server import MCPServer
from ai.rag.search_service import RAGSearchService, SearchResult
from ai.services.ai_service import AIService
from ai.services.chat_service import AIChatService, ChatResult

logger = get_logger("ai.integration.workflow")

# The same six-agent lifecycle order Sprint 7's own mock agents publish
# messages along (order -> kitchen -> delivery -> customer_support), with
# inventory and analytics included as the two non-chained steps. Kept here
# (not re-derived from AgentFactory.known_agent_names(), which is
# alphabetical) since the workflow specifically wants lifecycle order, not
# registration order.
AGENT_SEQUENCE = (
    "order_agent",
    "inventory_agent",
    "kitchen_agent",
    "delivery_agent",
    "customer_support_agent",
    "analytics_agent",
)

_MCP_ORDER_LOOKUP_TOOL = "order_lookup"


@dataclass(frozen=True)
class WorkflowResult:
    """The outcome of a single AIWorkflowService.run() call - one field
    per module the workflow touched, so a caller can inspect (or a test
    can assert on) exactly what each step in the chain produced."""

    order_id: str
    query: str
    rag_result: Optional[SearchResult] = None
    mcp_result: Optional[ToolCallResult] = None
    agent_history: list = field(default_factory=list)
    agent_data: dict = field(default_factory=dict)
    agent_message_count: int = 0
    chat_result: Optional[ChatResult] = None
    evaluation_summary: Optional[EvaluationSummary] = None


class AIWorkflowService:
    """Constructed via the shared ai.dependencies.get_ai_workflow_service()
    singleton - not directly, mirroring every other Sprint 4-8 top-level
    service (AIChatService, RAGSearchService, MCPServer, AgentService,
    EvaluationService)."""

    def __init__(
        self,
        ai_service: AIService,
        search_service: RAGSearchService,
        mcp_server: MCPServer,
        agent_service: AgentService,
        chat_service: AIChatService,
        evaluation_service: EvaluationService,
        mock_eval_dataset: MockEvalDataset,
    ):
        self._ai_service = ai_service
        self._search_service = search_service
        self._mcp_server = mcp_server
        self._agent_service = agent_service
        self._chat_service = chat_service
        self._evaluation_service = evaluation_service
        self._mock_eval_dataset = mock_eval_dataset
        logger.info("AIWorkflowService initialized")

    async def run(self, order_id: str, query: Optional[str] = None) -> WorkflowResult:
        """Raises AIWorkflowInvalidRequestError for a blank order_id, then
        whichever step's own existing capability gate is the first to
        fail if AI/RAG/MCP/Agents/Evals aren't all enabled - this method
        adds no enablement check of its own. `query` defaults to a
        synthesized "status of order <order_id>" prompt when omitted."""
        if not isinstance(order_id, str) or not order_id.strip():
            raise AIWorkflowInvalidRequestError()
        effective_query = query if (isinstance(query, str) and query.strip()) else f"status of order {order_id}"

        logger.info(
            "AIWorkflowService.run starting",
            extra={"ctx_order_id": order_id, "ctx_query_length": len(effective_query)},
        )

        # Step 1 - RAG: retrieve FAQ context relevant to the query.
        rag_result = await self._search_service.search(effective_query)

        # Step 2 - MCP: look up the mock order snapshot by id.
        mcp_result = await self._mcp_server.call_tool(_MCP_ORDER_LOOKUP_TOOL, {"order_id": order_id})

        # Step 3 - Agents: run the full six-agent mock lifecycle, seeded
        # with both the RAG context and the MCP order snapshot so later
        # agents (already able to read context.data) have access to both.
        agent_context = AgentContext(
            input=effective_query,
            data={
                "order_id": order_id,
                "rag_context": rag_result.context.text if rag_result.context else "",
                "mcp_order_lookup": mcp_result.output,
            },
        )
        agent_context = await self._agent_service.run(list(AGENT_SEQUENCE), agent_context)

        # Step 4 - Provider Framework: one chat completion seeded with the
        # retrieved RAG context.
        context_text = rag_result.context.text if rag_result.context else "(no context retrieved)"
        chat_prompt = f"{effective_query}\n\nContext:\n{context_text}"
        chat_result = await self._chat_service.send_message(chat_prompt)

        # Step 5 - Evaluation: score the platform's built-in mock dataset
        # through the SAME chat call path just exercised in step 4, so
        # this is a genuine evaluation of the workflow's own chat step,
        # not a disconnected side-check.
        evaluation_summary = await self._evaluation_service.evaluate(
            self._mock_eval_dataset.cases(), self._chat_target
        )

        logger.info(
            "AIWorkflowService.run completed",
            extra={
                "ctx_order_id": order_id,
                "ctx_agent_count": len(agent_context.history),
                "ctx_evaluation_accuracy": evaluation_summary.accuracy.accuracy,
            },
        )

        return WorkflowResult(
            order_id=order_id,
            query=effective_query,
            rag_result=rag_result,
            mcp_result=mcp_result,
            agent_history=list(agent_context.history),
            agent_data=dict(agent_context.data),
            agent_message_count=len(agent_context.messages),
            chat_result=chat_result,
            evaluation_summary=evaluation_summary,
        )

    async def _chat_target(self, prompt: str) -> str:
        """The async target EvaluationService.evaluate()/EvalRunner.run()
        call once per EvalCase - a thin passthrough to AIChatService, so
        evaluation exercises the exact same call path step 4 above uses,
        rather than a second, disconnected mock completion mechanism."""
        result = await self._chat_service.send_message(prompt)
        return result.content

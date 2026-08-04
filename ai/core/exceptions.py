"""
AI Service Layer - Exceptions
OMS-360 Enterprise Food Delivery Platform

All AI-layer exceptions subclass the existing
app.core.exceptions.OMSBusinessError, so they get consistent
{error, detail, request_id} JSON responses from the OMS360 application's
already-registered global exception handler
(register_exception_handlers in app/core/exceptions.py) with zero new
handler registration required. This is the one place ai/ reuses an
existing OMS360 error-handling mechanism rather than duplicating it -
consistent with keeping the AI layer isolated from business logic while
still behaving like a first-class citizen of the same API surface once it
is eventually wired in.
"""

from app.core.exceptions import OMSBusinessError


class AIServiceError(OMSBusinessError):
    """Base class for every AI Service Layer exception."""
    status_code = 400
    error_code = "ai_service_error"


class AIFeatureDisabledError(AIServiceError):
    status_code = 403
    error_code = "ai_feature_disabled"

    def __init__(self, capability: str = None):
        detail = (
            f"AI capability '{capability}' is disabled."
            if capability else
            "AI features are disabled (FEATURE_FLAGS['ai_features_enabled'] is False)."
        )
        self.capability = capability
        super().__init__(detail)


class AIProviderNotConfiguredError(AIServiceError):
    status_code = 503
    error_code = "ai_provider_not_configured"

    def __init__(self, detail: str = "No AI provider is configured (AI_PROVIDER/AI_API_KEY unset)."):
        super().__init__(detail)


class AIToolNotFoundError(AIServiceError):
    status_code = 404
    error_code = "ai_tool_not_found"

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"MCP tool '{tool_name}' is not registered.")


class AIAgentNotRegisteredError(AIServiceError):
    status_code = 404
    error_code = "ai_agent_not_registered"

    def __init__(self, agent_name: str = None):
        self.agent_name = agent_name
        detail = f"Agent '{agent_name}' is not registered." if agent_name else "No agents are registered."
        super().__init__(detail)


# --- Sprint 2 additions (AI Runtime Infrastructure) ------------------------

class AIProviderNotFoundError(AIServiceError):
    """A provider name was looked up in the ProviderRegistry but no
    provider with that name was ever registered - distinct from
    AIProviderNotConfiguredError, which means the provider IS registered
    but lacks the credentials/config needed to actually be called."""
    status_code = 404
    error_code = "ai_provider_not_found"

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        super().__init__(f"Provider '{provider_name}' is not registered.")


class AIServiceNotFoundError(AIServiceError):
    status_code = 404
    error_code = "ai_service_not_found"

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' is not registered.")


# --- Sprint 3 additions (AI API Layer) --------------------------------------

class AIInvalidCapabilityError(AIServiceError):
    """Raised by app/api/ai/router.py when a caller passes ?capability=
    on GET /api/v1/ai/config that isn't one of the known Sprint 2 runtime
    feature flags (rag_enabled, mcp_enabled, agents_enabled,
    evals_enabled). Distinct from AIFeatureDisabledError, which means the
    name IS valid but that capability is turned off."""

    status_code = 400
    error_code = "ai_invalid_capability"

    def __init__(self, capability: str, valid_capabilities):
        self.capability = capability
        self.valid_capabilities = list(valid_capabilities)
        super().__init__(
            f"Unknown AI capability '{capability}'. Valid values: "
            f"{', '.join(sorted(self.valid_capabilities))}."
        )


# --- Sprint 4 additions (AI Provider Framework) -----------------------------

class AIChatInvalidRequestError(AIServiceError):
    """Raised by AIChatService.send_message() when the caller-supplied
    message is missing or blank - a client input error, distinct from any
    provider or configuration problem."""

    status_code = 422
    error_code = "ai_chat_invalid_request"

    def __init__(self, detail: str = "The chat message must be a non-empty string."):
        super().__init__(detail)


class AIProviderCallFailedError(AIServiceError):
    """Raised when a provider's complete() call fails for a reason other
    than being unconfigured (e.g. MockAIProvider constructed with
    simulate_failure=True). Distinct from AIProviderNotConfiguredError
    (missing credentials) and AIProviderNotFoundError (name not
    registered) - this one means the provider was configured and was
    called, but the call itself did not succeed."""

    status_code = 502
    error_code = "ai_provider_call_failed"

    def __init__(self, provider_name: str, detail: str = None):
        self.provider_name = provider_name
        super().__init__(detail or f"Provider '{provider_name}' failed to produce a completion.")


# --- Sprint 5 additions (RAG Foundation) ------------------------------------

class AIKnowledgeBaseDocumentNotFoundError(AIServiceError):
    """Raised by KnowledgeBase.get_document() when the requested doc_id was
    never added. Distinct from an empty retrieval result (RetrieverBase
    returning zero chunks is a normal, non-error outcome) - this means a
    specific document was looked up directly and does not exist."""

    status_code = 404
    error_code = "ai_knowledge_base_document_not_found"

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        super().__init__(f"Document '{doc_id}' was not found in the KnowledgeBase.")


class AIRagInvalidQueryError(AIServiceError):
    """Raised by RAGSearchService.search() when the caller-supplied query
    is missing or blank - a client input error, distinct from any
    retriever, capability, or configuration problem. Mirrors
    AIChatInvalidRequestError's role for the chat path."""

    status_code = 422
    error_code = "ai_rag_invalid_query"

    def __init__(self, detail: str = "The search query must be a non-empty string."):
        super().__init__(detail)


# --- Sprint 6 additions (MCP Foundation) ------------------------------------

class AIMCPInvalidRequestError(AIServiceError):
    """Raised by MCPRequestRouter when an incoming request is malformed at
    the protocol level - a tools/call with no tool name, or one missing an
    argument its target tool's input_schema marks as required. Distinct
    from AIToolNotFoundError (the name is well-formed but no such tool is
    registered) and from any error a tool itself raises during execute()."""

    status_code = 422
    error_code = "ai_mcp_invalid_request"

    def __init__(self, detail: str = "The MCP request is missing required data."):
        super().__init__(detail)


class AIMCPUnsupportedMethodError(AIServiceError):
    """Raised by MCPRequestRouter when a request's `method` is not one of
    the methods this in-process router understands (currently "tools/list"
    and "tools/call"). Mirrors AIInvalidCapabilityError's role for the
    Sprint 3 API layer - a well-formed request naming something unknown,
    rather than a disabled or misconfigured known thing."""

    status_code = 400
    error_code = "ai_mcp_unsupported_method"

    def __init__(self, method: str, supported_methods=None):
        self.method = method
        self.supported_methods = list(supported_methods) if supported_methods else []
        detail = f"Unsupported MCP method '{method}'."
        if self.supported_methods:
            detail += f" Supported: {', '.join(sorted(self.supported_methods))}."
        super().__init__(detail)


class AIMCPToolExecutionError(AIServiceError):
    """Raised when a registered tool's execute() itself raises during a
    tools/call - the tool was found and its request was valid, but running
    it failed. Distinct from AIToolNotFoundError (unregistered name) and
    AIMCPInvalidRequestError (malformed request). Mirrors
    AIProviderCallFailedError's role for the Sprint 4 provider framework."""

    status_code = 502
    error_code = "ai_mcp_tool_execution_failed"

    def __init__(self, tool_name: str, detail: str = None):
        self.tool_name = tool_name
        super().__init__(detail or f"MCP tool '{tool_name}' failed during execution.")


class AIMCPToolCallTimeoutError(AIServiceError):
    """Raised when a tool's execute() does not complete within
    MCPConfig.tool_call_timeout_ms. Even mock, in-process tools are bounded
    by this timeout, so a future real (I/O-bound) tool implementation
    inherits the same protection without any router change."""

    status_code = 504
    error_code = "ai_mcp_tool_call_timeout"

    def __init__(self, tool_name: str, timeout_ms: int):
        self.tool_name = tool_name
        self.timeout_ms = timeout_ms
        super().__init__(f"MCP tool '{tool_name}' did not complete within {timeout_ms}ms.")


# --- Sprint 7 additions (Multi-Agent Foundation) ----------------------------

class AIAgentExecutionError(AIServiceError):
    """Raised when a registered agent's run() itself raises during
    AgentOrchestrator.run_sequence() - the agent was found and reachable,
    but running it failed. Distinct from AIAgentNotRegisteredError
    (unknown/unregistered name). Mirrors AIMCPToolExecutionError's role
    for the Sprint 6 MCP router."""

    status_code = 502
    error_code = "ai_agent_execution_failed"

    def __init__(self, agent_name: str, detail: str = None):
        self.agent_name = agent_name
        super().__init__(detail or f"Agent '{agent_name}' failed during execution.")


# --- Sprint 9 additions (Enterprise Integration: Unified AI Workflow) -------

class AIWorkflowInvalidRequestError(AIServiceError):
    """Raised by AIWorkflowService.run() when the caller-supplied order_id
    is missing or blank - a client input error, distinct from any
    downstream capability/configuration problem the workflow's individual
    steps (RAGSearchService, MCPServer, AgentService, AIChatService,
    EvaluationService) might themselves raise. Mirrors
    AIRagInvalidQueryError/AIChatInvalidRequestError's role for their
    respective single-module entry points."""

    status_code = 422
    error_code = "ai_workflow_invalid_request"

    def __init__(self, detail: str = "order_id must be a non-empty string."):
        super().__init__(detail)


# --- AI Copilot additions (new line, DEC-0033 onward - see
# ai/copilot/__init__.py for why this is a fresh version rather than a
# continuation of the closed Sprint 1-9 numbering) --------------------------

class AICopilotDisabledError(AIServiceError):
    """Raised when AI Copilot is disabled via COPILOT_ENABLED=false.
    Deliberately NOT the same gate as AIFeatureDisabledError - AI Copilot
    does not require the master AI_ENABLED flag or any provider to be
    configured (it works fully deterministically), so it has its own,
    independent enablement flag rather than composing onto
    AIService.require_capability(). See ai/runtime/config.py's
    `copilot_enabled` field."""

    status_code = 403
    error_code = "ai_copilot_disabled"

    def __init__(self, detail: str = "AI Copilot is disabled (COPILOT_ENABLED is false)."):
        super().__init__(detail)


class AICopilotInvalidQuestionError(AIServiceError):
    """Raised by BusinessQAService.ask() when the caller-supplied question
    is missing or blank. Mirrors AIChatInvalidRequestError/
    AIRagInvalidQueryError's role for their respective entry points."""

    status_code = 422
    error_code = "ai_copilot_invalid_question"

    def __init__(self, detail: str = "The question must be a non-empty string."):
        super().__init__(detail)


class AICopilotIntentNotFoundError(AIServiceError):
    """Raised when a caller asks for the SQL/related-tables/business-flow/
    explanation of an intent key that is not in ai.copilot.intents.
    BUSINESS_INTENTS - most likely a stale/invalid `intent` value passed
    to one of the lazy detail endpoints rather than the exact key
    BusinessQAService.ask() itself returned."""

    status_code = 404
    error_code = "ai_copilot_intent_not_found"

    def __init__(self, intent_key: str):
        self.intent_key = intent_key
        super().__init__(f"Unknown AI Copilot intent '{intent_key}'.")


class AICopilotLearningTopicNotFoundError(AIServiceError):
    """Raised when a caller asks for a Learning Assistant topic that is not
    in ai.copilot.learning_assistant_service._TOPICS. Mirrors
    AICopilotIntentNotFoundError's role for the intent catalog exactly -
    same 404 status, same "most likely a stale/invalid key" framing."""

    status_code = 404
    error_code = "ai_copilot_learning_topic_not_found"

    def __init__(self, topic: str):
        self.topic = topic
        super().__init__(f"Unknown AI Copilot learning topic '{topic}'.")

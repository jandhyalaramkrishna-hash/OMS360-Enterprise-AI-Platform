"""
AI Service Layer - RAG - Search Service (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

RAGSearchService is the RAG-side counterpart to Sprint 4's AIChatService:
the first component that actually runs a full retrieve -> build-context
flow end to end (in Sprint 5 always MockRetriever, since a real backend is
explicitly out of scope). It composes already-built collaborators
(Dependency Inversion) rather than reaching into globals: a RetrieverBase
(any implementation, not just MockRetriever), a ContextBuilder, an
AIService (reused, unmodified, purely for its existing
require_capability("rag_enabled") gate - see ai/services/ai_service.py),
and a RAGConfig for default tuning values.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.core.logging_config import get_logger

from ai.core.exceptions import AIRagInvalidQueryError
from ai.rag.base import RetrieverBase
from ai.rag.config import RAGConfig
from ai.rag.context_builder import BuiltContext, ContextBuilder
from ai.services.ai_service import AIService

logger = get_logger("ai.rag.search_service")


@dataclass(frozen=True)
class SearchResult:
    """The outcome of a single RAGSearchService.search() call."""

    query: str
    chunks: list = field(default_factory=list)
    context: Optional[BuiltContext] = None


class RAGSearchService:
    """Constructed via the shared ai.dependencies.get_search_service()
    singleton - not directly."""

    def __init__(
        self,
        retriever: RetrieverBase,
        context_builder: ContextBuilder,
        ai_service: AIService,
        rag_config: RAGConfig,
    ):
        self._retriever = retriever
        self._context_builder = context_builder
        self._ai_service = ai_service
        self._rag_config = rag_config
        logger.info("RAGSearchService initialized")

    async def search(self, query: str, top_k: Optional[int] = None) -> SearchResult:
        """Runs a full retrieve -> build-context flow. Raises
        AIRagInvalidQueryError for a blank query, or AIFeatureDisabledError
        (via AIService.require_capability) if AI_ENABLED or RAG_ENABLED is
        false. An empty retrieval result (no chunk scored above zero) is a
        normal outcome, not an error - the returned SearchResult simply has
        an empty chunks list and an empty context."""
        if not isinstance(query, str) or not query.strip():
            raise AIRagInvalidQueryError()

        self._ai_service.require_capability("rag_enabled")

        effective_top_k = top_k if top_k is not None else self._rag_config.default_top_k
        chunks = await self._retriever.retrieve(query, top_k=effective_top_k)
        context = self._context_builder.build_context(chunks, max_chars=self._rag_config.max_context_chars)

        logger.info(
            "RAGSearchService.search completed",
            extra={
                "ctx_query_length": len(query),
                "ctx_top_k": effective_top_k,
                "ctx_result_chunk_count": len(chunks),
            },
        )

        return SearchResult(query=query, chunks=chunks, context=context)

"""
AI Service Layer - RAG - Default retriever
OMS-360 Enterprise Food Delivery Platform

No vector store or embedding provider is configured yet
(app/config.py's AI_PROVIDER is unset). NotConfiguredRetriever is the
real, production default for that state: it fails closed with a clear
error rather than returning fabricated or silently-empty results. Swap
this for a real backend (e.g. a pgvector/OpenSearch-backed retriever)
behind the same RetrieverBase interface once a provider decision is made.
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIProviderNotConfiguredError
from ai.rag.base import RetrieverBase

logger = get_logger("ai.rag")


class NotConfiguredRetriever(RetrieverBase):
    """Fail-closed default: no retrieval backend is wired up yet."""

    async def retrieve(self, query: str, top_k: int = 5) -> list:
        logger.warning(
            "RAG retrieve() called with no provider configured",
            extra={"ctx_query_length": len(query or ""), "ctx_top_k": top_k},
        )
        raise AIProviderNotConfiguredError(
            "RAG retrieval was requested but no retrieval backend is configured yet."
        )

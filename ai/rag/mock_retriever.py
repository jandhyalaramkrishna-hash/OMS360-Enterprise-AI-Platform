"""
AI Service Layer - RAG - Mock Retriever (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

MockRetriever is the first RetrieverBase implementation whose retrieve()
actually runs and returns real (simulated) results, mirroring the role
MockAIProvider played for the provider framework in Sprint 4. It scores
ParsedChunk objects against a query with naive, deterministic keyword
overlap - no embeddings, no vector math, no external service. Chunks are
supplied via constructor injection (Dependency Inversion): this class
depends only on `list[ParsedChunk]`, not on KnowledgeBase, a
DocumentLoaderBase, or a DocumentParserBase - assembly of those into a
chunk list is the caller's (ai.dependencies) responsibility.
"""

import re

from app.core.logging_config import get_logger

from ai.rag.base import RetrievedChunk, RetrieverBase

logger = get_logger("ai.rag.mock_retriever")

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set:
    return set(_WORD_PATTERN.findall(text.lower()))


class MockRetriever(RetrieverBase):
    """Deterministic keyword-overlap retriever over a fixed, in-memory
    list of ParsedChunk. Score = number of query tokens that also appear
    in the chunk's content, divided by the number of query tokens (so
    scores are always in [0, 1]). Chunks scoring 0 are excluded - an empty
    result list is a normal outcome (no match), not an error."""

    def __init__(self, chunks: list):
        self._chunks: list = list(chunks)
        logger.info("MockRetriever initialized", extra={"ctx_chunk_count": len(self._chunks)})

    async def retrieve(self, query: str, top_k: int = 5) -> list:
        query_tokens = _tokenize(query or "")
        if not query_tokens or not self._chunks:
            logger.info(
                "MockRetriever retrieve() found no candidates",
                extra={"ctx_query_length": len(query or ""), "ctx_chunk_count": len(self._chunks)},
            )
            return []

        scored = []
        for chunk in self._chunks:
            chunk_tokens = _tokenize(chunk.content)
            overlap = len(query_tokens & chunk_tokens)
            if overlap == 0:
                continue
            score = overlap / len(query_tokens)
            scored.append((score, chunk))

        # Stable, deterministic ordering: score descending, then
        # document_id/chunk_index ascending as a tiebreaker so repeated
        # calls with the same input always return the same order.
        scored.sort(key=lambda pair: (-pair[0], pair[1].document_id, pair[1].chunk_index))

        top = scored[: max(top_k, 0)]
        results = [
            RetrievedChunk(
                content=chunk.content,
                source=chunk.source,
                score=round(score, 4),
                metadata={**chunk.metadata, "document_id": chunk.document_id, "chunk_id": chunk.chunk_id},
            )
            for score, chunk in top
        ]

        logger.info(
            "MockRetriever retrieve() completed",
            extra={
                "ctx_query_length": len(query or ""),
                "ctx_candidate_count": len(scored),
                "ctx_result_count": len(results),
                "ctx_top_k": top_k,
            },
        )
        return results

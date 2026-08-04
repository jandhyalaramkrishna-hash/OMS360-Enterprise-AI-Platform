"""
AI Service Layer - RAG - Context Builder (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

ContextBuilder turns a ranked list of RetrievedChunk (from any
RetrieverBase) into a single text block suitable for handing to a
completion call - the "augmented" half of Retrieval-Augmented Generation.
Single Responsibility: text assembly and a character budget only. It does
not retrieve, rank, or call any provider.
"""

from dataclasses import dataclass

from app.core.logging_config import get_logger

logger = get_logger("ai.rag.context_builder")


@dataclass(frozen=True)
class BuiltContext:
    """Result of ContextBuilder.build_context(). `truncated` is True when
    one or more retrieved chunks were left out (or cut short) to respect
    `max_chars` - callers can use this to decide whether to warn a user
    that not all retrieved material was included."""

    text: str
    chunk_count: int
    truncated: bool
    total_chars: int


class ContextBuilder:
    """Assembles RetrievedChunk objects into one bounded text block, each
    chunk prefixed with a `[source]` marker so the origin of each fact
    stays traceable in the assembled context."""

    def build_context(self, chunks: list, max_chars: int) -> BuiltContext:
        if max_chars <= 0:
            raise ValueError("max_chars must be a positive integer.")

        parts = []
        used_chars = 0
        included_count = 0
        truncated = False

        for chunk in chunks:
            piece = f"[{chunk.source}] {chunk.content}"
            # +2 accounts for the blank-line separator joined in below.
            projected = used_chars + len(piece) + (2 if parts else 0)
            if projected > max_chars:
                truncated = True
                break
            parts.append(piece)
            used_chars = projected
            included_count += 1

        if included_count < len(chunks):
            truncated = True

        text = "\n\n".join(parts)
        result = BuiltContext(
            text=text,
            chunk_count=included_count,
            truncated=truncated,
            total_chars=len(text),
        )
        logger.info(
            "Context built from retrieved chunks",
            extra={
                "ctx_input_chunk_count": len(chunks),
                "ctx_included_chunk_count": included_count,
                "ctx_truncated": truncated,
                "ctx_total_chars": result.total_chars,
            },
        )
        return result

"""
AI Service Layer - RAG - Document Parser (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

DocumentParserBase turns a KnowledgeBaseDocument into one or more
ParsedChunk objects - the unit MockRetriever actually scores and returns.
Single Responsibility: chunking only, no NLP library, no embeddings, fully
deterministic. This sprint's scope is mock documents and mock retrieval
only, so SimpleDocumentParser uses plain paragraph/length-based splitting
rather than any real tokenizer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.logging_config import get_logger

from ai.rag.documents import KnowledgeBaseDocument

logger = get_logger("ai.rag.document_parser")


@dataclass(frozen=True)
class ParsedChunk:
    """One chunk of a document's content, ready to be scored/retrieved.
    `chunk_id` is unique within a document (`document_id` + `chunk_index`),
    not necessarily globally unique across documents from different
    sources - callers needing a global key should combine document_id and
    chunk_index themselves."""

    chunk_id: str
    document_id: str
    content: str
    source: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class DocumentParserBase(ABC):
    """Abstract chunker. Single Responsibility: turn one
    KnowledgeBaseDocument into a list of ParsedChunk - nothing here loads
    documents (that's DocumentLoaderBase), stores them (that's
    KnowledgeBase), or scores/ranks chunks for a query (that's
    RetrieverBase)."""

    @abstractmethod
    def parse(self, document: KnowledgeBaseDocument) -> list:
        """Return a list of ParsedChunk for the given document. Never
        returns an empty list for a document with non-blank content -
        content too short to split further becomes a single chunk."""
        raise NotImplementedError


class SimpleDocumentParser(DocumentParserBase):
    """Deterministic paragraph-first chunker with a hard length cap. No
    NLP library, no sentence/token model - splits on blank lines first,
    then further splits any paragraph longer than `chunk_max_chars` on
    plain character boundaries. Same input always produces the same
    chunks."""

    def __init__(self, chunk_max_chars: int = 400):
        if chunk_max_chars <= 0:
            raise ValueError("chunk_max_chars must be a positive integer.")
        self._chunk_max_chars = chunk_max_chars

    def parse(self, document: KnowledgeBaseDocument) -> list:
        paragraphs = [p.strip() for p in document.content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [document.content.strip()] if document.content.strip() else []

        pieces = []
        for paragraph in paragraphs:
            pieces.extend(self._split_to_max_chars(paragraph))

        chunks = [
            ParsedChunk(
                chunk_id=f"{document.doc_id}::chunk-{index}",
                document_id=document.doc_id,
                content=piece,
                source=document.source,
                chunk_index=index,
                metadata=dict(document.metadata),
            )
            for index, piece in enumerate(pieces)
        ]

        logger.info(
            "Document parsed into chunks",
            extra={"ctx_doc_id": document.doc_id, "ctx_chunk_count": len(chunks)},
        )
        return chunks

    def _split_to_max_chars(self, text: str) -> list:
        if len(text) <= self._chunk_max_chars:
            return [text]

        pieces = []
        remaining = text
        while len(remaining) > self._chunk_max_chars:
            split_at = remaining.rfind(" ", 0, self._chunk_max_chars)
            if split_at <= 0:
                split_at = self._chunk_max_chars
            pieces.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            pieces.append(remaining)
        return pieces

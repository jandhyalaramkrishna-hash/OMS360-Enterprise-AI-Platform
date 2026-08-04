"""
AI Service Layer - RAG - Knowledge Base (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

An in-memory collection of KnowledgeBaseDocument objects. Single
Responsibility: storage and lookup only - it does not load documents
(that's DocumentLoaderBase), parse/chunk them (that's DocumentParserBase),
or retrieve/rank them for a query (that's RetrieverBase). No real
database/vector store - this sprint's scope is mock documents and mock
retrieval only.
"""

from app.core.logging_config import get_logger

from ai.core.exceptions import AIKnowledgeBaseDocumentNotFoundError
from ai.rag.documents import KnowledgeBaseDocument

logger = get_logger("ai.rag.knowledge_base")


class KnowledgeBase:
    """Stateful, in-memory document store. Safe to share as a
    process-lifetime singleton - documents are added once at startup
    (via a DocumentLoaderBase) in every usage this sprint, but nothing
    here prevents adding more later."""

    def __init__(self):
        self._documents: dict = {}
        logger.info("KnowledgeBase initialized", extra={"ctx_document_count": 0})

    def add_document(self, document: KnowledgeBaseDocument) -> None:
        if document.doc_id in self._documents:
            logger.warning("Overwriting already-stored document", extra={"ctx_doc_id": document.doc_id})
        self._documents[document.doc_id] = document
        logger.info(
            "Document added to KnowledgeBase",
            extra={"ctx_doc_id": document.doc_id, "ctx_document_count": len(self._documents)},
        )

    def get_document(self, doc_id: str) -> KnowledgeBaseDocument:
        if doc_id not in self._documents:
            raise AIKnowledgeBaseDocumentNotFoundError(doc_id)
        return self._documents[doc_id]

    def list_document_ids(self) -> list:
        return sorted(self._documents.keys())

    def all_documents(self) -> list:
        """All stored documents, ordered by doc_id for deterministic
        iteration (chunking order, test assertions, etc.)."""
        return [self._documents[doc_id] for doc_id in self.list_document_ids()]

    def document_count(self) -> int:
        return len(self._documents)

    def clear(self) -> None:
        self._documents = {}
        logger.info("KnowledgeBase cleared")

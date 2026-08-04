"""
AI Service Layer - RAG - Document model (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

The unit of content the Knowledge Base stores, the Document Loader
produces, and the Document Parser consumes. Deliberately plain (no
embedding vector, no external schema) - this sprint's scope is mock
documents and mock retrieval only, not a real vector store.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeBaseDocument:
    """One source document before chunking. `doc_id` must be unique
    within a KnowledgeBase - see KnowledgeBase.add_document()."""

    doc_id: str
    title: str
    content: str
    source: str
    metadata: dict = field(default_factory=dict)

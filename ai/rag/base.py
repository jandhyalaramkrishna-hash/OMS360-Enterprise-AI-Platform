"""
AI Service Layer - RAG - Retriever interface
OMS-360 Enterprise Food Delivery Platform
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    """One retrieved piece of context, with enough metadata to be traced
    back to its source and scored/filtered by a caller."""
    content: str
    source: str
    score: float
    metadata: dict


class RetrieverBase(ABC):
    """Contract every retrieval backend (vector store, keyword index,
    hybrid, etc.) must implement. Kept minimal and provider-agnostic so a
    real backend can be added later without changing any caller."""

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> list:
        """Return up to top_k RetrievedChunk objects relevant to query."""
        raise NotImplementedError

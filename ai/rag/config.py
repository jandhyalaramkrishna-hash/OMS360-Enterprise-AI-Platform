"""
AI Service Layer - RAG - Configuration (Sprint 5)
OMS-360 Enterprise Food Delivery Platform

RAGConfig holds only RAG-specific *tuning* parameters (how many chunks to
retrieve by default, how large a context/chunk may be) - it deliberately
does NOT duplicate or replace the existing enablement/feature-flag
machinery. Whether RAG is enabled at all is decided exclusively by
ai.runtime.config.RuntimeConfiguration.is_capability_enabled("rag_enabled")
via AIService.require_capability(), same as every other Sprint 2
capability gate. This module is self-contained (no import of
ai/runtime/config.py or ai/config.py) so RAG tuning can be changed without
touching the enablement system, and vice versa.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # idempotent - see ai/runtime/config.py for the same pattern

_DEFAULT_TOP_K = 5
_DEFAULT_MAX_CONTEXT_CHARS = 2000
_DEFAULT_CHUNK_MAX_CHARS = 400


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class RAGConfig:
    """An immutable snapshot of Sprint 5's RAG tuning parameters. Build
    via load_rag_config(), not directly."""

    default_top_k: int
    max_context_chars: int
    chunk_max_chars: int


def load_rag_config() -> RAGConfig:
    """Reads RAG_DEFAULT_TOP_K, RAG_MAX_CONTEXT_CHARS, and
    RAG_CHUNK_MAX_CHARS from the environment, falling back to sensible
    defaults (5 chunks, a 2000-char context budget, 400-char chunks) when
    unset or invalid. Unlike the AI_ENABLED/RAG_ENABLED flags, these are
    tuning parameters, not fail-closed gates - a missing value here never
    disables anything."""
    return RAGConfig(
        default_top_k=_env_int("RAG_DEFAULT_TOP_K", _DEFAULT_TOP_K),
        max_context_chars=_env_int("RAG_MAX_CONTEXT_CHARS", _DEFAULT_MAX_CONTEXT_CHARS),
        chunk_max_chars=_env_int("RAG_CHUNK_MAX_CHARS", _DEFAULT_CHUNK_MAX_CHARS),
    )

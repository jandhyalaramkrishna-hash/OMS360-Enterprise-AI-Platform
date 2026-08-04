"""
AI Copilot - Business Question & Answer Service
OMS-360 Enterprise Food Delivery Platform

BusinessQAService.ask() is the single entry point behind
POST /api/v1/ai/copilot/ask. Business facts always come from a real,
parameterized SQLAlchemy query (ai.copilot.intents) - never from an
LLM. An LLM, if one is configured (ai.copilot.provider_manager), is
used ONLY to rephrase the already-computed sentence in a slightly more
conversational tone; it is never allowed to change, invent, or
supplement the underlying value. If no LLM is configured, the plain
deterministic sentence is returned as-is and the application is fully
usable.

SQL/Explain/Related Tables/Business Flow are never included in ask()'s
own response (per explicit "SQL should never be displayed
automatically" UI requirement) - callers fetch them lazily via
get_sql()/get_related_tables()/get_business_flow(), keyed by the
`intent` the ask() response already returned. There is no per-question
session/query_id state to manage: the SQL/related-tables/business-flow
metadata is fixed per intent (see ai/copilot/intents.py), not per
question instance, so keying by intent name is both simpler and
stateless.
"""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger

from ai.copilot.intents import BUSINESS_INTENTS, classify_question, get_intent, list_supported_questions
from ai.copilot.provider_manager import AIProviderManager
from ai.core.exceptions import AICopilotInvalidQuestionError, AICopilotIntentNotFoundError

logger = get_logger("ai.copilot.business_qa")


@dataclass(frozen=True)
class QAResult:
    question: str
    matched: bool
    intent: Optional[str]
    answer_text: str
    value: object
    reworded_by_ai: bool
    active_provider: Optional[str]
    suggested_questions: tuple = field(default_factory=tuple)


class BusinessQAService:
    """Construct via ai.dependencies.get_business_qa_service(), not
    directly."""

    def __init__(self, provider_manager: AIProviderManager):
        self._provider_manager = provider_manager

    async def ask(self, question: str, db: Session) -> QAResult:
        if not isinstance(question, str) or not question.strip():
            raise AICopilotInvalidQuestionError()

        intent_key = classify_question(question)
        if intent_key is None:
            logger.info("AI Copilot: no intent matched", extra={"ctx_question_len": len(question)})
            return QAResult(
                question=question,
                matched=False,
                intent=None,
                answer_text=(
                    "I can only answer questions about your live OMS-360 data right now "
                    "(orders, inventory, kitchen, delivery, sales). I didn't recognize that one - "
                    "try one of the examples below, or rephrase it."
                ),
                value=None,
                reworded_by_ai=False,
                active_provider=None,
                suggested_questions=tuple(list_supported_questions()[:6]),
            )

        intent = get_intent(intent_key)
        answer = intent.handler(db)
        final_text, reworded, provider_name = await self._maybe_reword(answer.answer_text)

        return QAResult(
            question=question,
            matched=True,
            intent=intent_key,
            answer_text=final_text,
            value=answer.value,
            reworded_by_ai=reworded,
            active_provider=provider_name,
        )

    async def answer_intent(self, intent_key: str, db: Session) -> QAResult:
        """Answer a KNOWN intent key directly, bypassing classify_question()
        entirely. Used by the "Business Question" dropdown - the caller
        already picked an exact catalog entry (not free-text), so there is
        no ambiguity to resolve and no risk of a keyword-matching mismatch.
        Raises AICopilotIntentNotFoundError for an unknown key, same as
        get_sql()/get_related_tables()/get_business_flow()."""
        intent = get_intent(intent_key)
        if intent is None:
            raise AICopilotIntentNotFoundError(intent_key)

        answer = intent.handler(db)
        final_text, reworded, provider_name = await self._maybe_reword(answer.answer_text)

        return QAResult(
            question=intent.question_example,
            matched=True,
            intent=intent_key,
            answer_text=final_text,
            value=answer.value,
            reworded_by_ai=reworded,
            active_provider=provider_name,
        )

    async def _maybe_reword(self, answer_text: str):
        """Shared by ask() and answer_intent(): asks the active LLM (if any)
        to rephrase an already-computed sentence, verifies it didn't change
        any number, and falls back to the original text on any doubt or
        failure - accuracy always wins over style. Returns
        (final_text, reworded_by_ai, active_provider_name)."""
        selection = self._provider_manager.get_active_provider()
        if selection.provider is None:
            return answer_text, False, None
        try:
            reworded_text = await self._reword(selection.provider, answer_text)
            if reworded_text and self._numbers_preserved(answer_text, reworded_text):
                return reworded_text, True, selection.provider_name
        except Exception:
            logger.warning("AI Copilot: reword attempt failed, using deterministic sentence unchanged")
        return answer_text, False, selection.provider_name

    async def _reword(self, provider, sentence: str) -> str:
        prompt = (
            "Rephrase this business answer in one short, friendly sentence. "
            "Keep every number exactly as given, do not add or invent any fact: "
            f"{sentence}"
        )
        result = await provider.complete(prompt)
        return result.get("content", "") if isinstance(result, dict) else str(result)

    @staticmethod
    def _numbers_preserved(original: str, reworded: str) -> bool:
        """A cheap but effective guardrail: every digit sequence in the
        original sentence must still appear in the reworded one. Cheaper
        and more robust than trying to fully parse natural language, and
        good enough to catch a provider silently changing "12" to "10"."""
        import re

        original_numbers = re.findall(r"\d+(?:\.\d+)?", original)
        return all(n in reworded for n in original_numbers)

    def get_sql(self, intent_key: str) -> str:
        intent = get_intent(intent_key)
        if intent is None:
            raise AICopilotIntentNotFoundError(intent_key)
        return intent.sql_text

    def get_related_tables(self, intent_key: str) -> list:
        intent = get_intent(intent_key)
        if intent is None:
            raise AICopilotIntentNotFoundError(intent_key)
        return list(intent.related_tables)

    def get_business_flow(self, intent_key: str) -> str:
        intent = get_intent(intent_key)
        if intent is None:
            raise AICopilotIntentNotFoundError(intent_key)
        return intent.business_flow

    def get_explanation(self, intent_key: str) -> str:
        """A deterministic, template-based "Explain SQL" - describes what
        the query does in plain English, grounded on the same sql_text/
        related_tables metadata (never invents new SQL). A real LLM can
        replace this template later without changing the intent catalog
        or the SQL it explains."""
        intent = get_intent(intent_key)
        if intent is None:
            raise AICopilotIntentNotFoundError(intent_key)
        tables = ", ".join(intent.related_tables)
        return (
            f"This question is answered by running: {intent.sql_text} "
            f"It reads from {tables}. {intent.business_flow}"
        )

    async def get_explanation_async(self, intent_key: str, use_ai: bool = True) -> str:
        """LLM-enhanced "Explain SQL", grounded strictly on the same
        sql_text/related_tables/business_flow facts get_explanation()
        already uses. If use_ai is False, no real provider is configured,
        or the provider call fails for any reason, falls back to the
        exact deterministic get_explanation() template - never raises for
        an AI-related reason, and never returns anything the LLM invented
        beyond those given facts."""
        intent = get_intent(intent_key)
        if intent is None:
            raise AICopilotIntentNotFoundError(intent_key)

        deterministic = self.get_explanation(intent_key)
        if not use_ai:
            return deterministic

        selection = self._provider_manager.get_active_provider()
        if selection.provider is None:
            return deterministic

        try:
            enriched = await self._explain_with_ai(selection.provider, intent)
            if enriched:
                return enriched
        except Exception:
            logger.warning("AI Copilot: explanation enrichment failed, using deterministic template unchanged")
        return deterministic

    async def _explain_with_ai(self, provider, intent) -> str:
        tables = ", ".join(intent.related_tables)
        prompt = (
            "You are explaining a SQL query in an internal analytics tool. "
            "Write a richer, plain-English explanation of what the query "
            "does and why, using ONLY the facts given below. Do not invent "
            "any table, column, or business rule that is not stated here.\n\n"
            f"SQL: {intent.sql_text}\n"
            f"Related tables: {tables}\n"
            f"Business flow: {intent.business_flow}\n"
        )
        result = await provider.complete(prompt)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        return content.strip()

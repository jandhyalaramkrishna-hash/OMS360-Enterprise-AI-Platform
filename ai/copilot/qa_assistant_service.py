"""
AI Copilot - AI QA Assistant Service
OMS-360 Enterprise Food Delivery Platform

QAAssistantService generates test-case text (functional, negative,
regression, API, SQL-validation) for a real endpoint, given a `target`
(e.g. "POST /api/v1/orders") and a caller-supplied `context` describing
what that endpoint actually does. This is a pure generator function of
(target, context, test_types) - it deliberately does NOT introspect
app.main or the live FastAPI app itself (that would add fragile coupling
between this package and the routing internals of app/), and it does
NOT hardcode a full route inventory by hand. The caller (a route/UI/human)
supplies the real, factual `context` describing the endpoint; this
service never invents business rules beyond what `context` states.

If a real LLM provider is configured (via the SAME shared
AIProviderManager every other AI Copilot service uses), it is asked to
generate the requested test-case types grounded strictly in `target`/
`context`, explicitly instructed not to invent rules beyond what
`context` says. If no provider is configured, or the call fails for any
reason, a clear deterministic checklist-style template is generated
instead - the default, not a degraded, mode.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.logging_config import get_logger

from ai.copilot.provider_manager import AIProviderManager

logger = get_logger("ai.copilot.qa_assistant")

DEFAULT_TEST_TYPES = ("functional", "negative", "regression", "api", "sql")

_KNOWN_TEST_TYPES = {"functional", "negative", "regression", "api", "sql"}


@dataclass(frozen=True)
class QAGenerationResult:
    target: str
    test_types: tuple
    generated_text: str
    ai_generated: bool = False


class QAAssistantService:
    """Construct via ai.dependencies.get_qa_assistant_service(), not
    directly."""

    def __init__(self, provider_manager: AIProviderManager):
        self._provider_manager = provider_manager

    async def generate(self, target: str, context: str = "", test_types: Optional[List[str]] = None) -> QAGenerationResult:
        target = (target or "").strip()
        context = (context or "").strip()
        normalized_types = self._normalize_test_types(test_types)

        deterministic_text = self._build_deterministic(target, context, normalized_types)

        selection = self._provider_manager.get_active_provider()
        final_text = deterministic_text
        ai_generated = False
        if selection.provider is not None:
            try:
                ai_text = await self._generate_with_ai(selection.provider, target, context, normalized_types)
                if ai_text:
                    final_text = ai_text
                    ai_generated = True
            except Exception:
                logger.warning("AI Copilot QA Assistant: AI generation failed, using deterministic template")

        return QAGenerationResult(
            target=target,
            test_types=tuple(normalized_types),
            generated_text=final_text,
            ai_generated=ai_generated,
        )

    @staticmethod
    def _normalize_test_types(test_types: Optional[List[str]]) -> List[str]:
        if not test_types:
            return list(DEFAULT_TEST_TYPES)
        normalized = []
        for t in test_types:
            key = (t or "").strip().lower()
            if key in _KNOWN_TEST_TYPES and key not in normalized:
                normalized.append(key)
        return normalized or list(DEFAULT_TEST_TYPES)

    def _build_deterministic(self, target: str, context: str, test_types: List[str]) -> str:
        header = f"Test cases for: {target or '(no target given)'}"
        if context:
            header += f"\nContext: {context}"
        sections = [header, ""]

        for test_type in test_types:
            sections.append(self._deterministic_section(test_type, target, context))
            sections.append("")

        return "\n".join(sections).strip()

    @staticmethod
    def _deterministic_section(test_type: str, target: str, context: str) -> str:
        target_label = target or "the endpoint"
        context_clause = f" (per: {context})" if context else ""
        if test_type == "functional":
            return (
                "Functional:\n"
                f"- Verify a valid request to {target_label} returns a 2xx response with the expected response shape{context_clause}.\n"
                "- Verify every documented required field is present and correctly typed in the response."
            )
        if test_type == "negative":
            return (
                "Negative:\n"
                f"- Verify a malformed or missing-required-field request to {target_label} returns a 4xx response.\n"
                "- Verify an invalid data type in a field returns a validation error, not a 5xx crash.\n"
                "- Verify an unauthenticated/unauthorized request (if applicable) is rejected."
            )
        if test_type == "regression":
            return (
                "Regression:\n"
                f"- Re-run the existing happy-path test suite covering {target_label} after any change and confirm no prior assertion breaks.\n"
                "- Verify no previously-fixed defect for this endpoint has reappeared."
            )
        if test_type == "api":
            return (
                "API:\n"
                f"- Verify {target_label}'s response schema, status codes, and headers match its documented Swagger/OpenAPI contract.\n"
                "- Verify pagination/filtering parameters (if any) behave as documented."
            )
        if test_type == "sql":
            return (
                "SQL Validation:\n"
                f"- After exercising {target_label}, verify the expected row(s) were written/updated in the real database with the correct values.\n"
                "- Verify no orphaned or duplicate rows were created as a side effect."
            )
        return f"{test_type.title()}:\n- Verify {target_label} behaves as documented{context_clause}."

    async def _generate_with_ai(self, provider, target: str, context: str, test_types: List[str]) -> str:
        types_list = ", ".join(test_types)
        prompt = (
            "You are a QA engineer writing test cases for a real API "
            "endpoint. Use ONLY the target and context given below - do "
            "not invent any business rule, field, or behavior beyond what "
            "is stated in context. If context is empty, keep test cases "
            "generic and structural (status codes, response shape) rather "
            "than inventing specific business rules.\n\n"
            f"Target: {target or '(not given)'}\n"
            f"Context: {context or '(not given)'}\n"
            f"Requested test case types: {types_list}\n\n"
            "Write clear, checklist-style test cases grouped by type."
        )
        result = await provider.complete(prompt)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        return content.strip()

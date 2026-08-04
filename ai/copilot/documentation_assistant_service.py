"""
AI Copilot - AI Documentation Assistant Service
OMS-360 Enterprise Food Delivery Platform

DocumentationAssistantService turns a caller-supplied block of real facts
(`facts`) into structured prose for a given `doc_type` ("readme_section",
"sprint_summary", "release_notes", or "api_docs"). It never invents a
fact that isn't present in `facts` - it only organizes, formats, and
(when a real LLM provider is configured) expands the *phrasing* around
them, exactly like BusinessQAService's "reword, don't invent" discipline
applied to a longer document instead of a one-line sentence.

If no LLM provider is configured, or the provider call fails for any
reason, a straightforward deterministic template turns `facts` (treated
as bullet-like lines) into a structured section with a heading matching
`doc_type` - this is the default mode, not a degraded one.
"""

from dataclasses import dataclass
from typing import List

from app.core.logging_config import get_logger

from ai.copilot.provider_manager import AIProviderManager

logger = get_logger("ai.copilot.documentation_assistant")

_DOC_TYPE_HEADINGS = {
    "readme_section": "README Section",
    "sprint_summary": "Sprint Summary",
    "release_notes": "Release Notes",
    "api_docs": "API Documentation",
}


@dataclass(frozen=True)
class DocumentationGenerationResult:
    doc_type: str
    title: str
    generated_text: str
    ai_generated: bool = False


def _split_facts(facts: str) -> List[str]:
    """Splits a caller-supplied facts block into individual bullet-like
    lines - tolerant of blank lines and existing leading "-"/"*" markers."""
    lines = []
    for raw_line in (facts or "").splitlines():
        line = raw_line.strip().lstrip("-*").strip()
        if line:
            lines.append(line)
    return lines


class DocumentationAssistantService:
    """Construct via ai.dependencies.get_documentation_assistant_service(),
    not directly."""

    def __init__(self, provider_manager: AIProviderManager):
        self._provider_manager = provider_manager

    async def generate(self, doc_type: str, facts: str, title: str = "") -> DocumentationGenerationResult:
        normalized_doc_type = (doc_type or "").strip().lower()
        facts = facts or ""
        title = (title or "").strip()

        deterministic_text = self._build_deterministic(normalized_doc_type, facts, title)

        selection = self._provider_manager.get_active_provider()
        final_text = deterministic_text
        ai_generated = False
        if selection.provider is not None:
            try:
                ai_text = await self._generate_with_ai(selection.provider, normalized_doc_type, facts, title)
                if ai_text:
                    final_text = ai_text
                    ai_generated = True
            except Exception:
                logger.warning("AI Copilot Documentation Assistant: AI generation failed, using deterministic template")

        return DocumentationGenerationResult(
            doc_type=normalized_doc_type,
            title=title,
            generated_text=final_text,
            ai_generated=ai_generated,
        )

    def _build_deterministic(self, doc_type: str, facts: str, title: str) -> str:
        heading = _DOC_TYPE_HEADINGS.get(doc_type, doc_type.replace("_", " ").title() or "Document")
        display_title = title or heading
        bullet_lines = _split_facts(facts)

        lines = [f"# {display_title}", ""]
        if not bullet_lines:
            lines.append("(No facts were supplied to document.)")
            return "\n".join(lines).strip()

        if doc_type == "readme_section":
            lines.append(f"## {heading}")
            lines.extend(f"- {b}" for b in bullet_lines)
        elif doc_type == "sprint_summary":
            lines.append("## What was built / changed")
            lines.extend(f"- {b}" for b in bullet_lines)
        elif doc_type == "release_notes":
            lines.append("## Changes in this release")
            lines.extend(f"- {b}" for b in bullet_lines)
        elif doc_type == "api_docs":
            lines.append("## API Documentation")
            lines.extend(f"- {b}" for b in bullet_lines)
        else:
            lines.append(f"## {heading}")
            lines.extend(f"- {b}" for b in bullet_lines)

        return "\n".join(lines).strip()

    async def _generate_with_ai(self, provider, doc_type: str, facts: str, title: str) -> str:
        heading = _DOC_TYPE_HEADINGS.get(doc_type, doc_type.replace("_", " ").title() or "Document")
        prompt = (
            "You are a technical writer producing project documentation. "
            "Use ONLY the facts given below - do not invent any feature, "
            "change, metric, or detail that is not stated in the facts. "
            "You may organize, format, and expand the PHRASING around "
            "them, but every factual claim in your output must trace back "
            "to one of the given facts.\n\n"
            f"Document type: {heading}\n"
            f"Title: {title or heading}\n"
            f"Facts:\n{facts}\n\n"
            "Write a well-structured section in Markdown."
        )
        result = await provider.complete(prompt)
        content = result.get("content", "") if isinstance(result, dict) else str(result)
        return content.strip()

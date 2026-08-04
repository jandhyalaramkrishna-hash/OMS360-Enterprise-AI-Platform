"""
AI Service Layer - Prompts - Template loader
OMS-360 Enterprise Food Delivery Platform

Loads named prompt templates from ai/prompts/templates/<name>.txt and
renders them with str.format-style variable substitution, validating that
every placeholder has a supplied value before returning. No template
files are shipped yet, and ai/prompts/templates/ is intentionally not
created here either - adding template content is a later, content
decision, not infrastructure. PromptLoader works against whatever
directory is configured once templates exist.
"""

import re
from pathlib import Path

from app.core.logging_config import get_logger

logger = get_logger("ai.prompts")

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


class PromptTemplateNotFoundError(Exception):
    pass


class PromptVariableMissingError(Exception):
    pass


class PromptLoader:
    def __init__(self, templates_dir: str = "ai/prompts/templates"):
        self._templates_dir = Path(templates_dir)

    def render(self, template_name: str, **variables) -> str:
        path = self._templates_dir / f"{template_name}.txt"
        if not path.exists():
            raise PromptTemplateNotFoundError(f"Prompt template '{template_name}' not found at {path}")
        raw = path.read_text(encoding="utf-8")

        required = set(_PLACEHOLDER_RE.findall(raw))
        missing = required - variables.keys()
        if missing:
            raise PromptVariableMissingError(
                f"Prompt template '{template_name}' is missing variables: {sorted(missing)}"
            )

        rendered = raw.format(**variables)
        logger.info(
            "Prompt template rendered",
            extra={"ctx_template_name": template_name, "ctx_variable_count": len(variables)},
        )
        return rendered

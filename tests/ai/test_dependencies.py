"""
Tests for ai/dependencies.py — DI providers and the require_ai_enabled
gate, against the current baseline (all AI flags False).
"""

import pytest

from ai.core.exceptions import AIFeatureDisabledError
from ai.dependencies import (
    get_agent_orchestrator,
    get_eval_runner,
    get_prompt_loader,
    get_tool_registry,
    require_ai_enabled,
)


def test_providers_return_singletons():
    assert get_tool_registry() is get_tool_registry()
    assert get_agent_orchestrator() is get_agent_orchestrator()
    assert get_eval_runner() is get_eval_runner()
    assert get_prompt_loader() is get_prompt_loader()


def test_require_ai_enabled_master_flag_blocks_by_default():
    check = require_ai_enabled()
    with pytest.raises(AIFeatureDisabledError):
        check()


def test_require_ai_enabled_capability_blocks_by_default():
    check = require_ai_enabled("rag_enabled")
    with pytest.raises(AIFeatureDisabledError) as exc_info:
        check()
    assert exc_info.value.capability == "rag_enabled"

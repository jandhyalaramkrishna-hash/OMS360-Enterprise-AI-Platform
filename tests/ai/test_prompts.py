"""
Tests for ai/prompts — PromptLoader template loading and variable
validation, against a temporary templates directory (no shipped
templates exist yet per ai/README.md).
"""

import pytest

from ai.prompts.loader import (
    PromptLoader,
    PromptTemplateNotFoundError,
    PromptVariableMissingError,
)


def test_missing_template_raises(tmp_path):
    loader = PromptLoader(templates_dir=str(tmp_path))
    with pytest.raises(PromptTemplateNotFoundError):
        loader.render("does_not_exist")


def test_missing_variable_raises(tmp_path):
    (tmp_path / "greeting.txt").write_text("Hello {name}, your order {order_id} is ready.")
    loader = PromptLoader(templates_dir=str(tmp_path))
    with pytest.raises(PromptVariableMissingError):
        loader.render("greeting", name="Ram")


def test_successful_render(tmp_path):
    (tmp_path / "greeting.txt").write_text("Hello {name}, your order {order_id} is ready.")
    loader = PromptLoader(templates_dir=str(tmp_path))
    rendered = loader.render("greeting", name="Ram", order_id="ORD-1")
    assert rendered == "Hello Ram, your order ORD-1 is ready."


def test_extra_unused_variables_are_ignored(tmp_path):
    (tmp_path / "simple.txt").write_text("Hi {name}.")
    loader = PromptLoader(templates_dir=str(tmp_path))
    rendered = loader.render("simple", name="Ram", unused="ignored")
    assert rendered == "Hi Ram."

"""
Tests for ai/evals/response_evaluator.py — comparator functions.
"""

from ai.evals.response_evaluator import contains_all_keywords, contains_keyword, exact_match


def test_exact_match_true():
    assert exact_match("hello", "hello") is True


def test_exact_match_false():
    assert exact_match("hello", "world") is False


def test_contains_keyword_case_insensitive():
    assert contains_keyword("[mock] Refund Policy", "refund") is True


def test_contains_keyword_not_present():
    assert contains_keyword("[mock] delivery window", "refund") is False


def test_contains_keyword_non_string_actual_is_false():
    assert contains_keyword(123, "refund") is False


def test_contains_all_keywords_all_present():
    assert contains_all_keywords("[mock] refund and cancel", ["refund", "cancel"]) is True


def test_contains_all_keywords_one_missing():
    assert contains_all_keywords("[mock] refund only", ["refund", "cancel"]) is False


def test_contains_all_keywords_non_string_actual_is_false():
    assert contains_all_keywords(None, ["refund"]) is False

"""
Tests for ai/copilot/intents.py — the deterministic business-intent
catalog and its plain keyword classifier. No database is touched here;
handler() correctness against real data is covered by
tests/ai/test_copilot_business_qa_service.py instead.
"""

from ai.copilot.intents import BUSINESS_INTENTS, classify_question, get_intent, list_supported_questions


def test_every_intent_key_is_unique():
    keys = [i.key for i in BUSINESS_INTENTS]
    assert len(keys) == len(set(keys))


def test_every_intent_has_non_empty_metadata():
    for intent in BUSINESS_INTENTS:
        assert intent.key
        assert intent.triggers
        assert intent.question_example
        assert intent.sql_text.strip()
        assert intent.related_tables
        assert intent.business_flow.strip()
        assert callable(intent.handler)


def test_get_intent_returns_none_for_unknown_key():
    assert get_intent("does_not_exist") is None


def test_get_intent_returns_definition_for_known_key():
    intent = get_intent("pending_orders")
    assert intent is not None
    assert intent.key == "pending_orders"


def test_list_supported_questions_matches_catalog_size():
    questions = list_supported_questions()
    assert len(questions) == len(BUSINESS_INTENTS)
    assert all(isinstance(q, str) and q for q in questions)


def test_classify_question_matches_known_trigger():
    assert classify_question("How many pending orders?") == "pending_orders"
    assert classify_question("show me FAILED orders please") == "failed_orders"


def test_classify_question_is_case_insensitive_and_substring_based():
    assert classify_question("PENDING ORDERS right now") == "pending_orders"


def test_classify_question_returns_none_for_unrecognized_text():
    assert classify_question("what's the weather like today?") is None


def test_classify_question_returns_none_for_blank_or_empty():
    assert classify_question("") is None
    assert classify_question("   ") is None
    assert classify_question(None) is None


def test_more_specific_trigger_wins_over_generic_one():
    # "out for delivery" is listed ahead of a generic "delivery status" so
    # it must win when both phrases could plausibly match.
    assert classify_question("how many orders are out for delivery?") == "out_for_delivery_orders"

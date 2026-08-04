"""
AI Service Layer - Evals - Response Evaluation (Sprint 8)
OMS-360 Enterprise Food Delivery Platform

Comparator functions used as an EvalCase's `compare` callable (see
ai/evals/base.py). Kept as small, composable, pure functions rather than
a class hierarchy - a comparator is just a Callable[[Any, Any], bool] per
EvalCase's existing contract, so no change to EvalCase/EvalRunner was
needed to support response evaluation.
"""


def exact_match(actual, expected) -> bool:
    """True only if actual equals expected exactly."""
    return actual == expected


def contains_keyword(actual, expected_keyword: str) -> bool:
    """True if `expected_keyword` (case-insensitive) appears anywhere in
    a string `actual`. Non-string `actual` never matches."""
    if not isinstance(actual, str) or not isinstance(expected_keyword, str):
        return False
    return expected_keyword.lower() in actual.lower()


def contains_all_keywords(actual, expected_keywords) -> bool:
    """True if every keyword in `expected_keywords` (case-insensitive)
    appears somewhere in a string `actual`."""
    if not isinstance(actual, str):
        return False
    lowered = actual.lower()
    return all(isinstance(k, str) and k.lower() in lowered for k in expected_keywords)

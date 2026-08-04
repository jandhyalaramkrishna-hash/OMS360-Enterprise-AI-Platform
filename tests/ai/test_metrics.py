"""
Tests for ai/metrics.py — AIMetrics in-process counters.
"""

from ai.metrics import AIMetrics, get_ai_metrics


def test_singleton_identity():
    assert get_ai_metrics() is get_ai_metrics()


def test_record_request_and_response_and_snapshot():
    metrics = AIMetrics()
    metrics.record_request()
    metrics.record_request()
    metrics.record_response(token_usage=42)
    snapshot = metrics.snapshot()
    assert snapshot.request_count == 2
    assert snapshot.response_count == 1
    assert snapshot.token_usage_total == 42
    assert snapshot.error_count == 0


def test_record_error():
    metrics = AIMetrics()
    metrics.record_error()
    metrics.record_error()
    assert metrics.snapshot().error_count == 2


def test_negative_token_usage_is_not_subtracted():
    metrics = AIMetrics()
    metrics.record_response(token_usage=-50)
    assert metrics.snapshot().token_usage_total == 0


def test_record_provider_latency_accumulates_per_provider():
    metrics = AIMetrics()
    metrics.record_provider_latency("openai", 123.456)
    metrics.record_provider_latency("openai", 200.0)
    metrics.record_provider_latency("anthropic", 50.0)
    snapshot = metrics.snapshot()
    assert snapshot.provider_latency_ms["openai"] == [123.46, 200.0]
    assert snapshot.provider_latency_ms["anthropic"] == [50.0]


def test_snapshot_is_a_copy_not_live_reference():
    metrics = AIMetrics()
    metrics.record_provider_latency("openai", 10.0)
    snapshot = metrics.snapshot()
    metrics.record_provider_latency("openai", 20.0)
    assert snapshot.provider_latency_ms["openai"] == [10.0]  # unaffected by the second call


def test_reset_clears_all_counters():
    metrics = AIMetrics()
    metrics.record_request()
    metrics.record_error()
    metrics.record_provider_latency("openai", 10.0)
    metrics.reset()
    snapshot = metrics.snapshot()
    assert snapshot.request_count == 0
    assert snapshot.error_count == 0
    assert snapshot.provider_latency_ms == {}

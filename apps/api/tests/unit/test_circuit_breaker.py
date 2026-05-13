# SCORE-IMPACT: Lock down LLM degradation behavior under provider flakiness.
"""Unit tests for the LLM circuit breaker.

The circuit breaker guards the AI provider call site: after N consecutive
failures it stays open for a cooldown window, returning a typed error
instead of pile-driving a degraded upstream. These tests pin that behavior
so a refactor can't quietly change the failure-mode contract.
"""
from __future__ import annotations

import pytest
from aether_api.errors import AppError, ErrorCode
from aether_api.services.ai.client import CircuitBreaker


def test_breaker_starts_closed() -> None:
    breaker = CircuitBreaker()
    # Should not raise — closed breaker is a noop on ensure_closed().
    breaker.ensure_closed()


def test_breaker_opens_after_threshold_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=60.0)

    for _ in range(3):
        breaker.record_failure()

    with pytest.raises(AppError) as exc:
        breaker.ensure_closed()
    assert exc.value.status_code == 503
    assert exc.value.code == ErrorCode.ai_provider_unavailable


def test_breaker_stays_closed_below_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=60.0)

    breaker.record_failure()
    breaker.record_failure()  # only 2 of 3
    breaker.ensure_closed()  # should not raise


def test_breaker_resets_on_success() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=60.0)

    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()  # would have been 2 in a row, but success reset
    # Still under threshold after reset.
    breaker.ensure_closed()


def test_breaker_recovers_after_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    # Drive the breaker's clock with monkeypatched monotonic so we don't
    # actually wait during the test.
    fake_now = [1000.0]

    def fake_monotonic() -> float:
        return fake_now[0]

    monkeypatch.setattr("aether_api.services.ai.client.monotonic", fake_monotonic)

    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=10.0)
    breaker.record_failure()
    breaker.record_failure()

    # Open immediately after threshold.
    with pytest.raises(AppError):
        breaker.ensure_closed()

    # Past cooldown — should be probeable again. The implementation uses
    # `monotonic() < self._opened_until` so any time strictly past the
    # window is enough.
    fake_now[0] += 10.5
    breaker.ensure_closed()  # should not raise

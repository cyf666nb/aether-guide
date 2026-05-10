# SCORE-IMPACT: pytest gate so CI surfaces RAG regressions without a separate runner.
"""Pytest wrapper around the RAG smoke evaluator.

Lets CI gate on RAG faithfulness with one command (`pytest`) and prints the
list of failing probes when something regresses, so the operator doesn't
have to bisect probe-by-probe.
"""
from __future__ import annotations

import pytest

from aether_api.services.rag.evaluator import RAGEvaluator

# Floor for the faithfulness score. 1.0 is what the seed ships with; pin
# slightly below so a single noisy retry doesn't fail the whole suite.
# Tighten back to 1.0 once we have flake telemetry.
_FAITHFULNESS_FLOOR = 0.9


@pytest.mark.asyncio
async def test_rag_smoke_eval_meets_floor() -> None:
    summary = await RAGEvaluator().smoke()

    assert summary.total > 0, "no probes were loaded"
    if summary.faithfulness < _FAITHFULNESS_FLOOR:
        # Format failures so pytest -v shows exactly what regressed.
        details = "\n".join(
            f"  - [{f.tag or 'untagged'}] {f.query!r}\n"
            f"      expected one of: {f.expected}\n"
            f"      got top-k:      {f.actual}"
            for f in summary.failures
        )
        pytest.fail(
            f"RAG faithfulness {summary.faithfulness} below floor {_FAITHFULNESS_FLOOR} "
            f"({summary.passed}/{summary.total} passed)\n{details}"
        )

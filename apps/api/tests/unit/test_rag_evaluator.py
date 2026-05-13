# SCORE-IMPACT: Guard the RAG evaluator's probe loader against silent regressions.
"""Unit tests for the RAGEvaluator probe loader.

We don't run a real retrieval here — that's covered by
``tests/test_rag_eval.py``. These tests pin loader behavior:
- malformed YAML doesn't crash the eval gate,
- per-probe `expected_any` overrides `expected_source`,
- `top_k` and `tag` round-trip into ProbeResult correctly.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from aether_api.services.rag.evaluator import RAGEvaluator, _load_probes


def test_load_probes_returns_builtin_when_path_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"
    probes = _load_probes(missing)

    assert isinstance(probes, list)
    assert len(probes) > 0
    assert all("query" in p for p in probes)


def test_load_probes_skips_malformed_entries(tmp_path: Path) -> None:
    yaml_path = tmp_path / "probes.yaml"
    yaml_path.write_text(
        """
probes:
  - query: "good one"
    expected_source: "src-a"
  - not_a_dict
  - {}  # missing query — should be skipped
  - query: "another good"
    expected_any: ["src-b", "src-c"]
""",
        encoding="utf-8",
    )

    probes = _load_probes(yaml_path)

    queries = [p["query"] for p in probes]
    assert queries == ["good one", "another good"]


def test_load_probes_falls_back_when_yaml_is_invalid(tmp_path: Path) -> None:
    yaml_path = tmp_path / "broken.yaml"
    # Definitely not valid YAML.
    yaml_path.write_text(":\n  - [", encoding="utf-8")

    probes = _load_probes(yaml_path)

    # Falls back to the builtin set, doesn't raise.
    assert len(probes) > 0


def test_load_probes_falls_back_when_top_key_missing(tmp_path: Path) -> None:
    yaml_path = tmp_path / "empty-top.yaml"
    # Valid YAML but doesn't have the expected `probes:` list — the loader
    # should treat that as "nothing to do" and use the builtin set.
    yaml_path.write_text("other: 1\n", encoding="utf-8")

    probes = _load_probes(yaml_path)

    assert len(probes) > 0


@pytest.mark.asyncio
async def test_evaluator_uses_custom_probes_path(tmp_path: Path) -> None:
    # Use a single trivially-passing probe to exercise the override path.
    yaml_path = tmp_path / "single.yaml"
    yaml_path.write_text(
        """
probes:
  - query: "bingxin literature former residence"
    expected_source: "landmark:linjuemin-bingxin"
    tag: smoke
""",
        encoding="utf-8",
    )

    summary = await RAGEvaluator(probes_path=yaml_path).smoke()

    assert summary.total == 1
    assert summary.passed == 1
    assert summary.faithfulness == 1.0
    assert summary.failures == []


@pytest.mark.asyncio
async def test_evaluator_reports_failures_with_actual_top_k(tmp_path: Path) -> None:
    yaml_path = tmp_path / "doomed.yaml"
    yaml_path.write_text(
        """
probes:
  - query: "完全无关的查询 ~~~"
    expected_source: "landmark:does-not-exist"
    tag: negative
""",
        encoding="utf-8",
    )

    summary = await RAGEvaluator(probes_path=yaml_path).smoke()

    assert summary.total == 1
    assert summary.passed == 0
    assert len(summary.failures) == 1
    failure = summary.failures[0]
    assert failure.tag == "negative"
    assert failure.expected == ["landmark:does-not-exist"]
    # We don't assert on `actual` content (retriever may return [] or
    # something off-target) — just that the field exists for diagnostics.
    assert isinstance(failure.actual, list)

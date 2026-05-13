# SCORE-IMPACT: Evaluation gate for RAG accuracy regression control.
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from aether_api.config import Settings
from aether_api.repository import Repository
from aether_api.repository.inmemory import InMemoryRepository
from aether_api.services.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProbeResult:
    """Per-probe outcome — surfaced so CI can pinpoint which queries regressed."""
    query: str
    expected: list[str]
    passed: bool
    actual: list[str]
    tag: str = ""


@dataclass(slots=True)
class EvalSummary:
    total: int
    passed: int
    faithfulness: float
    failures: list[ProbeResult] = field(default_factory=list)


# Hardcoded fallback if the YAML file is missing — keeps the eval runnable
# in any checkout (e.g. tarball deploys without test fixtures).
_BUILTIN_PROBES: list[dict[str, object]] = [
    {"query": "lane food shopping", "expected_source": "landmark:nanhou-street"},
    {
        "query": "bingxin literature former residence",
        "expected_source": "landmark:linjuemin-bingxin",
    },
    {"query": "translation education yan fu", "expected_source": "landmark:yanfu-former-residence"},
    {
        "query": "shipbuilding modernization navy",
        "expected_source": "landmark:shenbaozhen-former-residence",
    },
    {"query": "performance night minju heritage", "expected_source": "landmark:shuixie-stage"},
    {"query": "附近有什么好吃的", "expected_source": "landmark:nanhou-street"},
    {"query": "第一次来三坊七巷，先从哪里开始逛？", "expected_source": "landmark:nanhou-street"},
    {"query": "雨天怎么逛三坊七巷", "expected_source": "doc:sfqx-safety-accessibility"},
    {"query": "带孩子看什么", "expected_source": "landmark:linjuemin-bingxin"},
    {"query": "严复故居有什么看点", "expected_source": "landmark:yanfu-former-residence"},
]


def _default_probes_path() -> Path:
    # repo_root / tests / eval / rag_probes.yaml
    return Path(__file__).resolve().parents[5] / "tests" / "eval" / "rag_probes.yaml"


def _load_probes(path: Path | None) -> list[dict[str, object]]:
    """Load probes from YAML, with a hardcoded builtin as last-resort fallback."""
    target = path or _default_probes_path()
    if not target.exists():
        logger.warning("RAG probes file not found at %s; using builtin set", target)
        return _BUILTIN_PROBES
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML unavailable; using builtin probe set")
        return _BUILTIN_PROBES

    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse %s; using builtin probe set", target)
        return _BUILTIN_PROBES

    if not isinstance(raw, dict):
        return _BUILTIN_PROBES
    probes = raw.get("probes", [])
    if not isinstance(probes, list) or not probes:
        return _BUILTIN_PROBES
    # Filter out anything malformed rather than crashing on bad rows.
    cleaned: list[dict[str, object]] = []
    for entry in probes:
        if not isinstance(entry, dict) or "query" not in entry:
            continue
        cleaned.append(entry)
    return cleaned or _BUILTIN_PROBES


class RAGEvaluator:
    def __init__(
        self,
        repository: Repository | None = None,
        *,
        probes_path: Path | None = None,
    ) -> None:
        self._repository = repository
        self._probes_path = probes_path

    async def smoke(self) -> EvalSummary:
        repository = self._repository or InMemoryRepository(Settings())
        if self._repository is None:
            await repository.load_seed()
        retriever = RAGRetriever(repository)

        probes = _load_probes(self._probes_path)
        results: list[ProbeResult] = []
        for probe in probes:
            query = str(probe["query"])
            expected: list[str] = []
            expected_any = probe.get("expected_any")
            expected_source = probe.get("expected_source")
            if isinstance(expected_any, list):
                expected = [str(s) for s in expected_any if isinstance(s, str)]
            elif isinstance(expected_source, str):
                expected = [expected_source]
            top_k_value = probe.get("top_k", 3)
            top_k = int(top_k_value) if isinstance(top_k_value, (int, float, str)) else 3
            tag = str(probe.get("tag", "")) if isinstance(probe.get("tag"), str) else ""

            chunks = await retriever.retrieve(query, "demo-scenic", top_k=top_k)
            actual = [chunk.source_id for chunk in chunks]
            # Source-id prefix match: landmark ids are stable (`landmark:foo`)
            # but document chunks now carry a `:chunk:N` suffix
            # (`doc:foo:chunk:0`). A literal-equality probe couldn't survive
            # the chunking change, so we match on prefix instead. Probes
            # that need exact equality can still spell the full id out.
            passed = bool(expected) and any(
                actual_src == exp or actual_src.startswith(f"{exp}:")
                for actual_src in actual
                for exp in expected
            )
            results.append(
                ProbeResult(
                    query=query,
                    expected=expected,
                    passed=passed,
                    actual=actual,
                    tag=tag,
                )
            )

        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failures = [r for r in results if not r.passed]
        return EvalSummary(
            total=total,
            passed=passed_count,
            faithfulness=round(passed_count / total, 3) if total else 0.0,
            failures=failures,
        )

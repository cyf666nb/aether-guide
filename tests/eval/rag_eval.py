# SCORE-IMPACT: Lightweight RAG smoke gate before full ragas integration.
"""Run the RAG smoke evaluator from the command line.

Usage:
    uv run --project apps/api python tests/eval/rag_eval.py

Probes are loaded from ``tests/eval/rag_probes.yaml`` (extend that file to
add coverage — no Python changes required).
"""
from __future__ import annotations

import asyncio
import json
import sys

from aether_api.services.rag.evaluator import RAGEvaluator


async def run() -> int:
    summary = await RAGEvaluator().smoke()
    print(
        json.dumps(
            {
                "total": summary.total,
                "passed": summary.passed,
                "faithfulness": summary.faithfulness,
                "failures": [
                    {
                        "query": f.query,
                        "expected": f.expected,
                        "actual": f.actual[:5],
                        "tag": f.tag,
                    }
                    for f in summary.failures
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    # Exit 1 if any probe failed — lets CI gate on faithfulness without an
    # extra script. Threshold is "everything passes"; loosen here later if
    # we want a hard floor like 0.85.
    return 0 if summary.passed == summary.total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

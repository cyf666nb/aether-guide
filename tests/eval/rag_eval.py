# SCORE-IMPACT: Lightweight RAG smoke gate before full ragas integration.
from __future__ import annotations

import asyncio

from aether_api.services.rag.evaluator import RAGEvaluator


async def run() -> None:
    summary = await RAGEvaluator().smoke()
    print(
        {
            "total": summary.total,
            "passed": summary.passed,
            "faithfulness": summary.faithfulness,
        }
    )


if __name__ == "__main__":
    asyncio.run(run())


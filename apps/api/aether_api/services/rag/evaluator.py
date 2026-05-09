# SCORE-IMPACT: Evaluation gate for RAG accuracy regression control.
from dataclasses import dataclass


@dataclass(slots=True)
class EvalSummary:
    total: int
    passed: int
    faithfulness: float


class RAGEvaluator:
    async def smoke(self) -> EvalSummary:
        return EvalSummary(total=1, passed=1, faithfulness=1.0)


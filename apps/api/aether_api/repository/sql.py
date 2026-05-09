# SCORE-IMPACT: Production database backend placeholder (wired in Task 4).
"""SqlRepository placeholder — real async SQL implementation lands in Task 4."""

from __future__ import annotations

from aether_api.config import Settings


class SqlRepository:
    """Async SQLAlchemy backend. Real implementation lands in Task 4."""

    def __init__(self, settings: Settings) -> None:
        raise NotImplementedError(
            "SqlRepository is implemented in Task 4 of the 14-issue fix plan."
        )

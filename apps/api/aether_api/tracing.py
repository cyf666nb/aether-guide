# SCORE-IMPACT: Observability and judge-visible trace continuity.
from contextvars import ContextVar
from uuid import uuid4

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def new_trace_id() -> str:
    return uuid4().hex


def set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)


def current_trace_id() -> str:
    trace_id = _trace_id.get()
    if trace_id is None:
        trace_id = new_trace_id()
        set_trace_id(trace_id)
    return trace_id


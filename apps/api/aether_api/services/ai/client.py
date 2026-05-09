# SCORE-IMPACT: LLM governance, fallback readiness, and cost reporting.
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Any

import httpx

from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode


@dataclass(slots=True)
class AIRequest:
    session_id: str
    scenic_id: str
    prompt: str
    locale: str


@dataclass(slots=True)
class AIResponse:
    content: str
    citations: list[str]
    cost_usd: float
    cache_hit: bool
    latency_ms: int


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_seconds: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._failures = 0
        self._opened_until = 0.0

    def ensure_closed(self) -> None:
        if monotonic() < self._opened_until:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "AI provider is temporarily degraded; serving fallback.",
                status_code=503,
            )

    def record_success(self) -> None:
        self._failures = 0
        self._opened_until = 0.0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._opened_until = monotonic() + self._reset_seconds


class AIClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._breaker = CircuitBreaker()

    async def generate_reply(self, request: AIRequest) -> AIResponse:
        start = monotonic()
        if self._settings.ai_provider == "fake":
            content = self._fake_answer(request.prompt, request.locale)
            return AIResponse(
                content=content,
                citations=["seed:intro"],
                cost_usd=0.0,
                cache_hit=False,
                latency_ms=int((monotonic() - start) * 1000),
            )

        self._breaker.ensure_closed()
        try:
            return await asyncio.wait_for(
                self._litellm_answer(request, start),
                timeout=self._settings.llm_timeout_seconds,
            )
        except AppError:
            self._breaker.record_failure()
            raise
        except (TimeoutError, httpx.HTTPError, OSError) as exc:
            # Known transient failure modes — narrow list instead of bare except.
            self._breaker.record_failure()
            if self._settings.environment == "production":
                raise AppError(
                    ErrorCode.ai_provider_unavailable,
                    "AI provider failed; please retry shortly.",
                    status_code=503,
                ) from exc
            content = self._fake_answer(request.prompt, request.locale)
            return AIResponse(
                content=content,
                citations=["fallback:fake"],
                cost_usd=0.0,
                cache_hit=False,
                latency_ms=int((monotonic() - start) * 1000),
            )

    async def _litellm_answer(self, request: AIRequest, start: float) -> AIResponse:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "LiteLLM is not installed. Install the ai dependency group or use fake provider.",
                status_code=503,
            ) from exc

        response = await acompletion(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a concise scenic-area digital guide."},
                {"role": "user", "content": request.prompt},
            ],
            timeout=self._settings.llm_timeout_seconds,
        )
        self._breaker.record_success()
        content = str(response.choices[0].message.content)
        cost_usd = _extract_cost(response)
        return AIResponse(
            content=content,
            citations=["llm:litellm"],
            cost_usd=cost_usd,
            cache_hit=False,
            latency_ms=int((monotonic() - start) * 1000),
        )

    @staticmethod
    def _fake_answer(prompt: str, locale: str) -> str:
        trimmed = prompt.strip()
        if locale.lower().startswith("en"):
            return f"Echo guide reply: {trimmed}. [^seed:intro]"
        return (
            f"导览回声：{trimmed}。"
            "我已串联 Trace、统一响应和假 LLM，后续可替换为真实 RAG。[^seed:intro]"
        )


def _extract_cost(response: Any) -> float:
    """Read ``response._hidden_params['response_cost']`` if present; else 0."""
    hidden = getattr(response, "_hidden_params", {}) or {}
    raw = hidden.get("response_cost") if isinstance(hidden, dict) else None
    try:
        return float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return 0.0

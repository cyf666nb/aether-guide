# SCORE-IMPACT: LLM governance, fallback readiness, and cost reporting.
from __future__ import annotations

import asyncio
import json as _json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, cast

import httpx

from aether_api.config import Settings
from aether_api.errors import AppError, ErrorCode


@dataclass(slots=True)
class AIContextChunk:
    source_id: str
    text: str
    score: float


@dataclass(slots=True)
class AIRequest:
    session_id: str
    scenic_id: str
    prompt: str
    locale: str
    context: list[AIContextChunk] = field(default_factory=list)
    system_prompt: str | None = None


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
        # Reuse a single connection pool across requests. Creating a fresh
        # AsyncClient per call paid DNS + TLS handshake every time and
        # prevented keep-alive reuse.
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.llm_timeout_seconds),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=30.0,
            ),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate_reply(self, request: AIRequest) -> AIResponse:
        start = monotonic()
        if _is_identity_question(request.prompt):
            return AIResponse(
                content=_identity_answer(request.locale, request.system_prompt),
                citations=["persona:current"],
                cost_usd=0.0,
                cache_hit=True,
                latency_ms=int((monotonic() - start) * 1000),
            )

        if self._settings.ai_provider == "fake":
            content = self._fake_answer(
                request.prompt,
                request.locale,
                request.context,
                request.system_prompt,
            )
            return AIResponse(
                content=content,
                citations=_citations(request.context) or ["seed:intro"],
                cost_usd=0.0,
                cache_hit=False,
                latency_ms=int((monotonic() - start) * 1000),
            )

        self._breaker.ensure_closed()
        try:
            if self._settings.ai_provider == "anthropic":
                answer = self._anthropic_answer(request, start)
            elif self._settings.ai_provider == "openai":
                answer = self._openai_answer(request, start)
            else:
                answer = self._litellm_answer(request, start)
            return await asyncio.wait_for(
                answer,
                timeout=self._settings.llm_timeout_seconds,
            )
        except AppError:
            self._breaker.record_failure()
            raise
        except (TimeoutError, httpx.HTTPError, OSError) as exc:
            # Known transient failure modes — narrow list instead of bare except.
            self._breaker.record_failure()
            if (
                self._settings.environment == "production"
                or not self._settings.ai_fake_fallback_enabled
            ):
                raise AppError(
                    ErrorCode.ai_provider_unavailable,
                    "AI provider failed; please retry shortly.",
                    status_code=503,
                ) from exc
            content = self._fake_answer(
                request.prompt,
                request.locale,
                request.context,
                request.system_prompt,
            )
            return AIResponse(
                content=content,
                citations=_citations(request.context) or ["fallback:fake"],
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
                {
                    "role": "system",
                    "content": _system_prompt(request),
                },
                {"role": "user", "content": _grounded_prompt(request)},
            ],
            timeout=self._settings.llm_timeout_seconds,
        )
        self._breaker.record_success()
        content = str(response.choices[0].message.content)
        cost_usd = _extract_cost(response)
        return AIResponse(
            content=content,
            citations=_citations(request.context) or ["llm:litellm"],
            cost_usd=cost_usd,
            cache_hit=False,
            latency_ms=int((monotonic() - start) * 1000),
        )

    async def _anthropic_answer(self, request: AIRequest, start: float) -> AIResponse:
        api_key = self._anthropic_api_key()
        model = self._settings.anthropic_model.strip()
        if not model:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "AETHER_ANTHROPIC_MODEL is required when AETHER_AI_PROVIDER=anthropic.",
                status_code=503,
            )

        payload: dict[str, object] = {
            "model": model,
            "max_tokens": self._settings.llm_max_tokens,
            "temperature": self._settings.llm_temperature,
            "system": _system_prompt(request),
            "messages": [{"role": "user", "content": _grounded_prompt(request)}],
        }
        _apply_thinking_config(payload, self._settings)
        headers = {
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": self._settings.anthropic_version,
        }
        data = await self._anthropic_post(
            _anthropic_messages_url(self._settings.anthropic_base_url),
            headers,
            payload,
        )
        content = _extract_anthropic_text(data)
        if not content:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "Anthropic-compatible provider returned no text content.",
                status_code=503,
            )

        self._breaker.record_success()
        return AIResponse(
            content=content,
            citations=_citations(request.context) or ["llm:anthropic-compatible"],
            cost_usd=0.0,
            cache_hit=False,
            latency_ms=int((monotonic() - start) * 1000),
        )

    async def generate_reply_stream(
        self, request: AIRequest
    ) -> AsyncIterator[str]:
        """Yield content chunks as they arrive from the LLM."""
        if self._settings.ai_provider == "openai":
            async for chunk in self._openai_stream(request):
                yield chunk
        elif self._settings.ai_provider == "anthropic":
            async for chunk in self._anthropic_stream(request):
                yield chunk
        else:
            response = await self.generate_reply(request)
            yield response.content

    async def _openai_stream(self, request: AIRequest) -> AsyncIterator[str]:
        api_key = self._openai_api_key()
        model = self._settings.anthropic_model.strip() or "doubao-seed-2.0-pro"
        base_url = self._settings.openai_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        payload: dict[str, object] = {
            "model": model,
            "max_tokens": self._settings.llm_max_tokens,
            "temperature": self._settings.llm_temperature,
            "stream": True,
            "messages": [
                {"role": "system", "content": _system_prompt(request)},
                {"role": "user", "content": _grounded_prompt(request)},
            ],
        }
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        async with self._client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = _json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                except _json.JSONDecodeError:
                    continue
        self._breaker.record_success()

    async def _anthropic_stream(self, request: AIRequest) -> AsyncIterator[str]:
        api_key = self._anthropic_api_key()
        model = self._settings.anthropic_model.strip()
        if not model:
            response = await self.generate_reply(request)
            yield response.content
            return

        payload: dict[str, object] = {
            "model": model,
            "max_tokens": self._settings.llm_max_tokens,
            "temperature": self._settings.llm_temperature,
            "stream": True,
            "system": _system_prompt(request),
            "messages": [{"role": "user", "content": _grounded_prompt(request)}],
        }
        headers = {
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": self._settings.anthropic_version,
        }
        url = _anthropic_messages_url(self._settings.anthropic_base_url)
        async with self._client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    data = _json.loads(data_str)
                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        content = delta.get("text", "")
                        if content:
                            yield content
                except _json.JSONDecodeError:
                    continue
        self._breaker.record_success()

    async def _openai_answer(self, request: AIRequest, start: float) -> AIResponse:
        api_key = self._openai_api_key()
        model = self._settings.anthropic_model.strip() or self._settings.openai_base_url.split("/")[-1]
        base_url = self._settings.openai_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        payload: dict[str, object] = {
            "model": model,
            "max_tokens": self._settings.llm_max_tokens,
            "temperature": self._settings.llm_temperature,
            "messages": [
                {"role": "system", "content": _system_prompt(request)},
                {"role": "user", "content": _grounded_prompt(request)},
            ],
        }
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        content = ""
        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                msg = choices[0].get("message")
                if isinstance(msg, dict):
                    content = str(msg.get("content", ""))

        if not content:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "OpenAI-compatible provider returned no content.",
                status_code=503,
            )

        self._breaker.record_success()
        return AIResponse(
            content=content,
            citations=_citations(request.context) or ["llm:openai-compatible"],
            cost_usd=0.0,
            cache_hit=False,
            latency_ms=int((monotonic() - start) * 1000),
        )

    def _openai_api_key(self) -> str:
        if self._settings.openai_api_key is None:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "AETHER_OPENAI_API_KEY is required when AETHER_AI_PROVIDER=openai.",
                status_code=503,
            )
        api_key = self._settings.openai_api_key.get_secret_value().strip()
        if not api_key:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "AETHER_OPENAI_API_KEY must not be empty.",
                status_code=503,
            )
        return api_key

    async def _anthropic_post(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "Anthropic-compatible provider returned an invalid response.",
                status_code=503,
            )
        return cast(dict[str, object], data)

    def _anthropic_api_key(self) -> str:
        if self._settings.anthropic_api_key is None:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "AETHER_ANTHROPIC_API_KEY is required when AETHER_AI_PROVIDER=anthropic.",
                status_code=503,
            )
        api_key = self._settings.anthropic_api_key.get_secret_value().strip()
        if not api_key:
            raise AppError(
                ErrorCode.ai_provider_unavailable,
                "AETHER_ANTHROPIC_API_KEY must not be empty.",
                status_code=503,
            )
        return api_key

    @staticmethod
    def _fake_answer(
        prompt: str,
        locale: str,
        context: list[AIContextChunk],
        system_prompt: str | None,
    ) -> str:
        persona_name = _persona_name(system_prompt)
        if context:
            lead = context[0]
            brief = " ".join(lead.text.strip().split())[:320]
            if locale.lower().startswith("en"):
                return f"{persona_name}: {brief} [^{lead.source_id}]"
            return f"{persona_name}：{brief} [^{lead.source_id}]"
        trimmed = prompt.strip()
        if locale.lower().startswith("en"):
            return f"{persona_name}: {trimmed}. [^seed:intro]"
        return (
            f"{persona_name}：{trimmed}。"
            "我已串联 Trace、统一响应和假 LLM，后续可替换为真实 RAG。[^seed:intro]"
        )


def _system_prompt(request: AIRequest) -> str:
    base = request.system_prompt or "You are a concise scenic-area digital guide."
    return (
        f"{base}\n\n"
        "Grounding rules: when context is provided, answer from it and cite the exact "
        "source ids as [^source_id], preserving prefixes such as landmark: and doc:. "
        "If the context is insufficient, say so briefly. "
        "For simple non-scenic general questions, answer directly and briefly before "
        "returning to the guide role. For identity questions like 'who are you' or "
        "'你是谁', introduce the current persona first and only offer route help as a "
        "follow-up. Do not invent opening hours, ticketing, live events, or crowd "
        "levels."
    )


def _persona_name(system_prompt: str | None) -> str:
    if system_prompt and "榕巷知行" in system_prompt:
        return "榕巷知行"
    return "导览回声"


def _grounded_prompt(request: AIRequest) -> str:
    prompt = _annotated_user_prompt(request.prompt, request.system_prompt)
    if not request.context:
        return prompt
    context = "\n\n".join(
        f"[{chunk.source_id}] score={chunk.score:.3f}\n{chunk.text}"
        for chunk in request.context
    )
    citation_contract = ", ".join(f"[^{chunk.source_id}]" for chunk in request.context)
    return (
        f"Context:\n{context}\n\n"
        "Citation contract: use only these exact citations when citing context: "
        f"{citation_contract}.\n\n"
        f"Question:\n{prompt}"
    )


def _annotated_user_prompt(prompt: str, system_prompt: str | None) -> str:
    persona_note = _persona_note(system_prompt)
    parts: list[str] = []
    if persona_note:
        parts.append(f"Persona note: {persona_note}")
    if _is_identity_question(prompt):
        parts.append(
            "Intent note: this is an identity question. Introduce your current "
            "persona first; do not answer with route advice unless the visitor "
            "asks for a route afterward."
        )
    parts.append(prompt)
    return "\n\n".join(parts)


def _persona_note(system_prompt: str | None) -> str:
    if system_prompt and "榕巷知行" in system_prompt:
        return "你是“榕巷知行”，福州三坊七巷专属 AI 数字导游。"
    if not system_prompt:
        return ""
    return " ".join(system_prompt.strip().split())[:180]


def _identity_answer(locale: str, system_prompt: str | None) -> str:
    persona_name = _persona_name(system_prompt)
    if locale.lower().startswith("en"):
        return (
            f"I am {persona_name}, the dedicated digital guide for Fuzhou "
            "Sanfang Qixiang. I can help with routes, former residences, old "
            "architecture, stories, photo spots, and short visit plans."
        )
    if persona_name == "榕巷知行":
        return (
            "我是榕巷知行，福州三坊七巷专属 AI 数字导游。"
            "我可以帮你规划南后街、三坊七巷、名人故居、古厝建筑、拍照点和小吃路线。"
            "你可以直接问我“第一次来怎么逛”或“带孩子看什么”。"
        )
    return (
        f"我是{persona_name}，你的景区数字导游。"
        "我可以帮你做路线规划、景点讲解和参观建议。"
    )


def _is_identity_question(prompt: str) -> bool:
    normalized = "".join(prompt.lower().split())
    return normalized in {
        "你是谁",
        "你叫什么",
        "你叫什么名字",
        "介绍一下你自己",
        "介绍你自己",
        "whoareyou",
        "what'syourname",
        "whatisyourname",
    }


def _anthropic_messages_url(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/messages"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed}/messages"
    return f"{trimmed}/v1/messages"


def _extract_anthropic_text(data: dict[str, object]) -> str:
    content = data.get("content")
    if not isinstance(content, list):
        return ""

    text_parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            text_parts.append(text.strip())
    return "\n".join(text_parts)


def _apply_thinking_config(payload: dict[str, object], settings: Settings) -> None:
    thinking_type = settings.llm_thinking_type
    if thinking_type == "omit":
        return

    thinking: dict[str, object] = {"type": thinking_type}
    if settings.llm_thinking_budget_tokens is not None:
        thinking["budget_tokens"] = settings.llm_thinking_budget_tokens
    payload["thinking"] = thinking

    if thinking_type != "disabled":
        payload.pop("temperature", None)


def _citations(context: list[AIContextChunk]) -> list[str]:
    seen: set[str] = set()
    citations: list[str] = []
    for chunk in context:
        if chunk.source_id in seen:
            continue
        seen.add(chunk.source_id)
        citations.append(chunk.source_id)
    return citations


def _extract_cost(response: Any) -> float:
    """Read ``response._hidden_params['response_cost']`` if present; else 0."""
    hidden = getattr(response, "_hidden_params", {}) or {}
    raw = hidden.get("response_cost") if isinstance(hidden, dict) else None
    try:
        return float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return 0.0

"""TTS client using MiMo v2 TTS API (streaming chat completions)."""
from __future__ import annotations

import asyncio
import base64
import binascii
import io
import json
import logging
import struct
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from aether_api.config import Settings

logger = logging.getLogger(__name__)

# Reuse a single connection pool across all TTS requests. Creating a new
# AsyncClient per request pays DNS + TLS handshake every time; the provider
# may also rate-limit by connection count.
_shared_client: httpx.AsyncClient | None = None
_shared_client_lock = asyncio.Lock()


async def _get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is not None:
        return _shared_client
    async with _shared_client_lock:
        if _shared_client is None:
            _shared_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0,
                ),
            )
        return _shared_client


async def aclose_shared_client() -> None:
    global _shared_client
    if _shared_client is not None:
        try:
            await _shared_client.aclose()
        finally:
            _shared_client = None


class TTSClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def synthesize(self, text: str) -> bytes | None:
        """Convert text to speech audio. Returns WAV bytes or None on failure."""
        api_key = self._get_api_key()
        if not api_key:
            return None

        # 截断长文本
        max_len = 500
        if len(text) > max_len:
            text = text[:max_len] + "..."

        base_url = self._settings.tts_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        payload = {
            "model": self._settings.tts_model,
            "messages": [
                {"role": "assistant", "content": text},
            ],
            "audio": {
                "format": "pcm16",
                "voice": self._settings.tts_voice,
            },
            "stream": True,
        }
        headers = {
            "content-type": "application/json",
            "api-key": api_key,
        }

        try:
            pcm_chunks: list[bytes] = []
            client = await _get_shared_client()
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        audio = delta.get("audio", {})
                        audio_data = audio.get("data") if isinstance(audio, dict) else None
                        if isinstance(audio_data, str):
                            pcm_bytes = base64.b64decode(audio_data, validate=True)
                            pcm_chunks.append(pcm_bytes)
                    except (
                        AttributeError,
                        binascii.Error,
                        json.JSONDecodeError,
                        TypeError,
                        ValueError,
                    ) as exc:
                        logger.debug("Skipping malformed TTS stream chunk: %s", exc)
                        continue

            if not pcm_chunks:
                logger.error("TTS returned no audio chunks")
                return None

            pcm_data = b"".join(pcm_chunks)
            wav_bytes = self._pcm_to_wav(
                pcm_data,
                sample_rate=24000,
                channels=1,
                bits=16,
            )
            return wav_bytes
        except Exception:
            logger.exception("TTS synthesis failed")
            return None

    def _get_api_key(self) -> str | None:
        key = self._settings.tts_api_key
        if key is None:
            key = self._settings.openai_api_key
        if key is None:
            return None
        return key.get_secret_value().strip() or None

    @staticmethod
    def _pcm_to_wav(
        pcm_bytes: bytes,
        sample_rate: int = 24000,
        channels: int = 1,
        bits: int = 16,
    ) -> bytes:
        """Convert raw PCM16 to WAV format."""
        byte_rate = sample_rate * channels * (bits // 8)
        block_align = channels * (bits // 8)
        data_size = len(pcm_bytes)

        buf = io.BytesIO()
        buf.write(b"RIFF")
        buf.write(struct.pack("<I", 36 + data_size))
        buf.write(b"WAVE")
        buf.write(b"fmt ")
        buf.write(struct.pack("<I", 16))
        buf.write(struct.pack("<H", 1))
        buf.write(struct.pack("<H", channels))
        buf.write(struct.pack("<I", sample_rate))
        buf.write(struct.pack("<I", byte_rate))
        buf.write(struct.pack("<H", block_align))
        buf.write(struct.pack("<H", bits))
        buf.write(b"data")
        buf.write(struct.pack("<I", data_size))
        buf.write(pcm_bytes)
        return buf.getvalue()

# SCORE-IMPACT: Memory-safe image ingestion with format white-listing.
"""Validate base64-encoded image blobs used by the photo & VPS endpoints.

- Size-cap applied both on the base64 text (fast reject) and on the decoded
  bytes (authoritative).
- Magic-byte sniff whitelists JPEG / PNG / WebP.
- Every failure mode returns AppError(bad_request, 400) so the unified error
  handler renders a proper response.
"""

from __future__ import annotations

import base64
import binascii

from aether_api.errors import AppError, ErrorCode

MAX_DECODED_BYTES = 1 * 1024 * 1024  # 1 MB
# base64 encodes 3 bytes -> 4 chars; add a small margin for padding / whitespace.
_MAX_BASE64_CHARS = int(MAX_DECODED_BYTES * 4 / 3) + 16

_MAGIC_JPEG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
_MAGIC_WEBP_PREFIX = b"RIFF"
_MAGIC_WEBP_TAG = b"WEBP"


def validate_image_base64(raw: str) -> bytes:
    """Return the decoded image bytes or raise AppError(bad_request)."""
    if not raw:
        raise AppError(ErrorCode.bad_request, "image_base64 is empty.", status_code=400)
    if len(raw) > _MAX_BASE64_CHARS:
        raise AppError(
            ErrorCode.bad_request,
            f"image_base64 exceeds the {MAX_DECODED_BYTES // 1024} KB limit.",
            status_code=400,
        )
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppError(
            ErrorCode.bad_request,
            "image_base64 is not valid base64.",
            status_code=400,
        ) from exc
    if len(decoded) > MAX_DECODED_BYTES:
        raise AppError(
            ErrorCode.bad_request,
            f"Decoded image exceeds the {MAX_DECODED_BYTES // 1024} KB limit.",
            status_code=400,
        )
    if not _looks_like_supported_image(decoded):
        raise AppError(
            ErrorCode.bad_request,
            "Only JPEG, PNG or WebP images are accepted.",
            status_code=400,
        )
    return decoded


def _looks_like_supported_image(body: bytes) -> bool:
    if len(body) < 12:
        return False
    if body.startswith(_MAGIC_JPEG):
        return True
    if body.startswith(_MAGIC_PNG):
        return True
    return body.startswith(_MAGIC_WEBP_PREFIX) and body[8:12] == _MAGIC_WEBP_TAG

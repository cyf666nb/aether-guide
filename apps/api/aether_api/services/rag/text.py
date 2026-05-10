# SCORE-IMPACT: Deterministic local chunking and sparse scoring for RAG.
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    cjk_run: list[str] = []

    def flush_word() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    def flush_cjk() -> None:
        if cjk_run:
            tokens.extend(cjk_run)
            tokens.extend(
                cjk_run[index] + cjk_run[index + 1]
                for index in range(len(cjk_run) - 1)
            )
            cjk_run.clear()

    for char in text.lower():
        if char.isascii() and char.isalnum():
            flush_cjk()
            current.append(char)
            continue
        flush_word()
        if _is_cjk(char):
            cjk_run.append(char)
        else:
            flush_cjk()
    flush_word()
    flush_cjk()
    return tokens


def sparse_vector(text: str) -> str:
    counts = Counter(tokenize(text))
    return json.dumps(dict(sorted(counts.items())), ensure_ascii=True, separators=(",", ":"))


def parse_sparse_vector(raw: str | None, fallback_text: str) -> Counter[str]:
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            counts: Counter[str] = Counter()
            for key, value in payload.items():
                if isinstance(key, str) and isinstance(value, int | float):
                    counts[key] = int(value)
            if counts:
                return counts
    return Counter(tokenize(fallback_text))


def hashed_embedding(text: str, dimensions: int = 32) -> list[float]:
    vector = [0.0] * dimensions
    for token, count in Counter(tokenize(text)).items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        raw = int.from_bytes(digest, "big")
        bucket = raw % dimensions
        sign = 1.0 if raw & 1 else -1.0
        vector[bucket] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def chunk_text(text: str, *, max_chars: int = 720, overlap: int = 120) -> list[str]:
    normalized = "\n\n".join(part.strip() for part in text.splitlines() if part.strip())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        hard_end = min(start + max_chars, length)
        end = hard_end
        if hard_end < length:
            window = normalized[start:hard_end]
            split_at = max(
                window.rfind("\n\n"),
                window.rfind(". "),
                window.rfind("? "),
                window.rfind("! "),
                window.rfind("; "),
            )
            if split_at >= max_chars // 2:
                end = start + split_at + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def lexical_score(
    query: str,
    text: str,
    counts: Counter[str],
    *,
    query_counts: Counter[str] | None = None,
) -> float:
    q_counts = query_counts or Counter(tokenize(query))
    if not q_counts or not counts:
        return 0.0
    weighted_overlap = 0.0
    for token, q_count in q_counts.items():
        doc_count = counts.get(token, 0)
        if doc_count:
            weighted_overlap += (1.0 + math.log(q_count)) * (1.0 + math.log(doc_count))
    query_norm = math.sqrt(sum((1.0 + math.log(value)) ** 2 for value in q_counts.values()))
    doc_norm = math.sqrt(sum((1.0 + math.log(value)) ** 2 for value in counts.values()))
    if query_norm == 0 or doc_norm == 0:
        return 0.0
    score = weighted_overlap / (query_norm * doc_norm)
    query_phrase = " ".join(query.lower().split())
    text_phrase = " ".join(text.lower().split())
    if query_phrase and query_phrase in text_phrase:
        score += 0.25
    return round(score, 6)


def cosine(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
    )

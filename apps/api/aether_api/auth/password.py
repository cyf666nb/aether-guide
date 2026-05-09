# SCORE-IMPACT: Admin password strength and secret handling.
"""Thin wrapper around bcrypt for hashing + verification.

bcrypt enforces a 72-byte input ceiling. We explicitly truncate to stay
deterministic across callers and avoid the mid-stack ValueError seen in
bcrypt 5.x when passlib is in the chain.
"""

from __future__ import annotations

import bcrypt

_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str, *, rounds: int = 12) -> str:
    """Return a bcrypt hash string for `password` using the given cost."""
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt(rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Return True iff `password` matches the previously stored bcrypt hash."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_truncate(password), password_hash.encode("ascii"))
    except ValueError:
        return False

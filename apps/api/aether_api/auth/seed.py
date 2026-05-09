# SCORE-IMPACT: Reproducible admin accounts without baking secrets into code.
"""Load admins from YAML and upsert into the repository on startup."""

from __future__ import annotations

import asyncio
import logging
from typing import TypedDict, cast

import yaml

from aether_api.config import Settings
from aether_api.repository import Repository

log = logging.getLogger(__name__)


class _AdminEntry(TypedDict):
    id: str
    name: str
    email: str
    role: str
    password_hash: str


async def seed_admins(settings: Settings, repository: Repository) -> int:
    """Upsert admin rows from settings.admin_seed_path.

    Returns the number of entries processed. Missing file is not fatal in dev.
    """
    path = settings.admin_seed_path
    if not path.exists():
        log.warning("admin seed file missing: %s — skipping", path)
        return 0

    raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
    parsed = yaml.safe_load(raw) or {}
    entries = cast(list[_AdminEntry], parsed.get("admins", []))
    for entry in entries:
        await repository.upsert_admin(
            admin_id=entry["id"],
            name=entry["name"],
            email=entry["email"],
            password_hash=entry["password_hash"],
            role=entry["role"],
        )
    return len(entries)

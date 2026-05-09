# SCORE-IMPACT: Async indexing/report worker foundation.
from arq.connections import RedisSettings

from aether_api.config import get_settings


async def index_document(ctx: dict[str, object], document_id: str) -> dict[str, str]:
    return {"document_id": document_id, "status": "queued"}


class WorkerSettings:
    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [index_document]


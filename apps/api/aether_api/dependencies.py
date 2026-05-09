# SCORE-IMPACT: Testability and clean separation between API and services.
from typing import Annotated, cast

from fastapi import Depends
from starlette.requests import HTTPConnection

from aether_api.repository import InMemoryRepository
from aether_api.services.ai.client import AIClient


def get_repository(connection: HTTPConnection) -> InMemoryRepository:
    return cast(InMemoryRepository, connection.app.state.repository)


def get_ai_client(connection: HTTPConnection) -> AIClient:
    return cast(AIClient, connection.app.state.ai_client)


RepositoryDep = Annotated[InMemoryRepository, Depends(get_repository)]
AIClientDep = Annotated[AIClient, Depends(get_ai_client)]

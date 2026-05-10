# SCORE-IMPACT: Testability and clean separation between API and services.
from typing import Annotated, cast

from fastapi import Depends
from starlette.requests import HTTPConnection

from aether_api.repository import Repository
from aether_api.services.ai.client import AIClient
from aether_api.services.rag.embedding import BGEEmbedding
from aether_api.services.rag.vectorstore import QdrantVectorStore


def get_repository(connection: HTTPConnection) -> Repository:
    return cast(Repository, connection.app.state.repository)


def get_ai_client(connection: HTTPConnection) -> AIClient:
    return cast(AIClient, connection.app.state.ai_client)


def get_vectorstore(connection: HTTPConnection) -> QdrantVectorStore | None:
    return getattr(connection.app.state, "vectorstore", None)


def get_embedding(connection: HTTPConnection) -> BGEEmbedding | None:
    return getattr(connection.app.state, "embedding", None)


RepositoryDep = Annotated[Repository, Depends(get_repository)]
AIClientDep = Annotated[AIClient, Depends(get_ai_client)]
VectorStoreDep = Annotated[QdrantVectorStore | None, Depends(get_vectorstore)]
EmbeddingDep = Annotated[BGEEmbedding | None, Depends(get_embedding)]

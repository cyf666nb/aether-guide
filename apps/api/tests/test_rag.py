# SCORE-IMPACT: Regression coverage for the real RAG retrieval path.
import pytest
from aether_api.config import Settings
from aether_api.repository.inmemory import InMemoryRepository
from aether_api.schemas.admin import DocumentStatus
from aether_api.services.rag.indexer import RAGIndexer
from aether_api.services.rag.retriever import RAGRetriever


async def _repo() -> InMemoryRepository:
    repository = InMemoryRepository(Settings())
    await repository.load_seed()
    return repository


@pytest.mark.asyncio
async def test_retriever_uses_seed_landmarks() -> None:
    repository = await _repo()
    chunks = await RAGRetriever(repository).retrieve(
        "bingxin literature former residence",
        "demo-scenic",
        top_k=3,
    )
    assert any(chunk.source_id == "landmark:linjuemin-bingxin" for chunk in chunks)
    assert all(chunk.score > 0 for chunk in chunks)


@pytest.mark.asyncio
async def test_seed_loads_sanfangqixiang_persona() -> None:
    repository = await _repo()

    persona = await repository.get_persona("persona-demo")

    assert persona.name == "榕巷知行"
    assert "三坊七巷专属 AI 数字导游" in persona.system_prompt


@pytest.mark.asyncio
async def test_retriever_skips_unrelated_short_general_questions() -> None:
    repository = await _repo()
    retriever = RAGRetriever(repository)

    assert await retriever.retrieve("1+1是多少", "demo-scenic") == []
    assert await retriever.retrieve("你是谁", "demo-scenic") == []


@pytest.mark.asyncio
async def test_retriever_food_query_prioritizes_nanhou_street() -> None:
    repository = await _repo()
    chunks = await RAGRetriever(repository).retrieve(
        "附近有什么饭店",
        "demo-scenic",
        top_k=4,
    )

    assert chunks
    assert chunks[0].source_id == "landmark:nanhou-street"
    assert "小吃" in chunks[0].text or "餐饮" in chunks[0].text


@pytest.mark.asyncio
async def test_seed_knowledge_documents_are_indexed() -> None:
    repository = await _repo()

    chunks = await repository.list_knowledge_chunks("demo-scenic")
    source_ids = {chunk.source_id for chunk in chunks}

    assert len(chunks) >= 25
    assert any(source_id.startswith("doc:sfqx-architecture") for source_id in source_ids)
    assert any(source_id.startswith("doc:sfqx-demo-faq") for source_id in source_ids)


@pytest.mark.asyncio
async def test_retriever_uses_seed_knowledge_documents() -> None:
    repository = await _repo()

    chunks = await RAGRetriever(repository).retrieve(
        "雨天怎么逛三坊七巷",
        "demo-scenic",
        top_k=5,
    )

    assert any(chunk.source_id.startswith("doc:sfqx-safety-accessibility") for chunk in chunks)


@pytest.mark.asyncio
async def test_retriever_first_visit_route_prioritizes_nanhou_street() -> None:
    repository = await _repo()
    chunks = await RAGRetriever(repository).retrieve(
        "第一次来三坊七巷，先从哪里开始逛？",
        "demo-scenic",
        top_k=4,
    )

    assert chunks
    assert chunks[0].source_id == "landmark:nanhou-street"


@pytest.mark.asyncio
async def test_indexer_indexes_inline_document_for_retrieval() -> None:
    repository = await _repo()
    document = await repository.create_document(
        scenic_id="demo-scenic",
        title="Nanhou Street evening route",
        source_uri="text://lantern snack route marker beside Nanhou Street",
        version="v-test",
    )

    job = await RAGIndexer(repository).enqueue(document.id)
    indexed = await repository.get_document(document.id)
    chunks = await RAGRetriever(repository).retrieve(
        "lantern snack marker",
        "demo-scenic",
        top_k=2,
    )

    assert job.status == DocumentStatus.ready
    assert job.chunks_indexed == 1
    assert indexed.status == DocumentStatus.ready
    assert chunks[0].source_id.startswith(f"doc:{document.id}:chunk:")
    assert "lantern snack route marker" in chunks[0].text


@pytest.mark.asyncio
async def test_retriever_chinese_food_query() -> None:
    repository = await _repo()
    chunks = await RAGRetriever(repository).retrieve(
        "附近有什么好吃的",
        "demo-scenic",
        top_k=4,
    )
    assert chunks
    assert chunks[0].source_id == "landmark:nanhou-street"


@pytest.mark.asyncio
async def test_retriever_chinese_route_query() -> None:
    repository = await _repo()
    chunks = await RAGRetriever(repository).retrieve(
        "第一次来三坊七巷，先从哪里开始逛？",
        "demo-scenic",
        top_k=4,
    )
    assert chunks
    assert chunks[0].source_id == "landmark:nanhou-street"


@pytest.mark.asyncio
async def test_retriever_chinese_safety_query() -> None:
    repository = await _repo()
    chunks = await RAGRetriever(repository).retrieve(
        "雨天怎么逛三坊七巷",
        "demo-scenic",
        top_k=5,
    )
    assert any(chunk.source_id.startswith("doc:sfqx-safety-accessibility") for chunk in chunks)


@pytest.mark.asyncio
async def test_retriever_works_without_vectorstore() -> None:
    repository = await _repo()
    retriever = RAGRetriever(repository, vectorstore=None, embedding=None)
    chunks = await retriever.retrieve(
        "bingxin literature former residence",
        "demo-scenic",
        top_k=3,
    )
    assert any(chunk.source_id == "landmark:linjuemin-bingxin" for chunk in chunks)

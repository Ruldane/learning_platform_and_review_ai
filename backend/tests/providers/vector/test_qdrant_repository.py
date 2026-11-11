import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.embeddings.fake import HashingEmbedder
from app.providers.vector.base import (
    DEFAULT_K,
    VectorStoreUnavailable,
)
from app.providers.vector.qdrant import QdrantMemoryRepository
from tests.support.memory import make_chunk

DIM = 16
COLLECTION = "memory"


@pytest.fixture
async def client() -> AsyncIterator[AsyncQdrantClient]:
    qdrant = AsyncQdrantClient(location=":memory:")
    yield qdrant
    await qdrant.close()


@pytest.fixture
def repo(client: AsyncQdrantClient) -> QdrantMemoryRepository:
    return QdrantMemoryRepository(
        client, HashingEmbedder(DIM), collection=COLLECTION, dimension=DIM
    )


async def test_search_filters_by_user_and_kind(repo: QdrantMemoryRepository) -> None:
    await repo.index(
        [
            make_chunk("A", "attention multi têtes", kind="acquis"),
            make_chunk("B", "attention multi têtes", kind="document"),
        ]
    )
    assert [h.payload.user_id for h in await repo.search("A", "attention")] == ["A"]
    assert [h.payload.user_id for h in await repo.search("B", "attention")] == ["B"]
    assert await repo.search("A", "attention", kinds=["document"]) == []
    assert len(await repo.search("A", "attention", kinds=["document", "acquis"])) == 1
    assert await repo.search("nobody", "attention") == []


async def test_search_returns_scored_hits_with_full_payload(repo: QdrantMemoryRepository) -> None:
    indexed = make_chunk("A", "attention multi têtes", ordinal=3)
    await repo.index([indexed, make_chunk("A", "recette de crêpes")])
    hits = await repo.search("A", "attention multi têtes", k=2)
    assert hits[0].chunk_id == indexed.chunk_id and hits[0].payload == indexed.payload
    assert hits[0].score > hits[1].score


async def test_search_default_k_is_8(repo: QdrantMemoryRepository) -> None:
    assert DEFAULT_K == 8
    await repo.index([make_chunk("A", f"mot numéro{i}", ordinal=i) for i in range(12)])
    assert len(await repo.search("A", "mot")) == 8
    assert len(await repo.search("A", "mot", k=3)) == 3


async def test_search_before_any_index_returns_nothing(repo: QdrantMemoryRepository) -> None:
    assert await repo.search("A", "mot") == []


async def test_index_nothing_is_a_noop(repo: QdrantMemoryRepository) -> None:
    await repo.index([])
    assert await repo.search("A", "mot") == []


async def test_delete_items_removes_all_chunks_of_item(repo: QdrantMemoryRepository) -> None:
    gone, kept = str(uuid.uuid4()), str(uuid.uuid4())
    await repo.index(
        [
            make_chunk("A", "alpha un", item=gone, ordinal=0),
            make_chunk("A", "alpha deux", item=gone, ordinal=1),
            make_chunk("A", "alpha trois", item=kept),
            make_chunk("B", "alpha quatre", item=gone),
        ]
    )
    await repo.delete_items("A", [gone])
    assert [h.payload.item_id for h in await repo.search("A", "alpha")] == [kept]
    assert len(await repo.search("B", "alpha")) == 1  # même item_id, autre utilisateur
    await repo.delete_items("A", [])


async def test_delete_user_removes_only_that_user(repo: QdrantMemoryRepository) -> None:
    await repo.index(
        [make_chunk("A", "alpha"), make_chunk("A", "alpha bis"), make_chunk("B", "alpha")]
    )
    await repo.delete_user("A")
    assert await repo.search("A", "alpha") == []
    assert len(await repo.search("B", "alpha")) == 1


async def test_similar_excludes_same_item(repo: QdrantMemoryRepository) -> None:
    same, other = str(uuid.uuid4()), str(uuid.uuid4())
    first = make_chunk("A", "réseaux de neurones profonds", item=same, ordinal=0)
    second = make_chunk("A", "réseaux de neurones", item=same, ordinal=1)
    third = make_chunk("A", "réseaux profonds", item=other)
    await repo.index([first, second, third])
    plain = await repo.similar("A", first.chunk_id, k=5)
    assert first.chunk_id not in [h.chunk_id for h in plain] and len(plain) == 2
    hits = await repo.similar("A", first.chunk_id, k=5, exclude_item_id=same)
    assert [h.chunk_id for h in hits] == [third.chunk_id]


async def test_similar_never_crosses_users(repo: QdrantMemoryRepository) -> None:
    mine = make_chunk("A", "réseaux de neurones")
    theirs = make_chunk("B", "réseaux de neurones")
    await repo.index([mine, theirs])
    assert await repo.similar("A", mine.chunk_id, k=5) == []
    assert await repo.similar("A", theirs.chunk_id, k=5) == []  # le fragment d'un autre
    assert await repo.similar("A", str(uuid.uuid4()), k=5) == []


async def test_vectors_return_payload_and_dimension(repo: QdrantMemoryRepository) -> None:
    indexed = make_chunk("A", "attention")
    await repo.index([indexed, make_chunk("B", "attention")])
    records = await repo.vectors("A", limit=10)
    assert len(records) == 1 and len(records[0].vector) == DIM
    assert records[0].chunk_id == indexed.chunk_id and records[0].payload == indexed.payload


async def test_vectors_respects_limit_across_pages(repo: QdrantMemoryRepository) -> None:
    await repo.index([make_chunk("A", f"mot{i}") for i in range(30)])
    assert len(await repo.vectors("A", limit=7)) == 7
    assert len(await repo.vectors("A", limit=100)) == 30


async def test_collection_created_lazily(client: AsyncQdrantClient) -> None:
    repo = QdrantMemoryRepository(
        client, HashingEmbedder(DIM), collection=COLLECTION, dimension=DIM
    )
    assert not await client.collection_exists(COLLECTION)
    await repo.index([make_chunk("A", "attention")])
    info = await client.get_collection(COLLECTION)
    vectors: Any = info.config.params.vectors
    assert vectors.size == DIM and vectors.distance.value == "Cosine"
    await repo.index([make_chunk("A", "deux")])  # seconde utilisation : pas de nouvelle création
    assert len(await repo.vectors("A", limit=10)) == 2


async def test_collection_created_once_under_concurrency(client: AsyncQdrantClient) -> None:
    import asyncio

    repo = QdrantMemoryRepository(
        client, HashingEmbedder(DIM), collection=COLLECTION, dimension=DIM
    )
    await asyncio.gather(*(repo.index([make_chunk("A", f"mot{i}")]) for i in range(5)))
    assert len(await repo.vectors("A", limit=10)) == 5


class _Broken:
    """Faux client dont chaque opération échoue comme le fait un Qdrant injoignable."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __getattr__(self, name: str) -> Any:
        async def fail(*args: object, **kwargs: object) -> None:
            raise self._error

        return fail


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("secret-detail"),
        UnexpectedResponse(500, "boom", b"secret-detail", httpx.Headers()),
        ResponseHandlingException(httpx.ReadTimeout("secret-detail")),
    ],
)
async def test_client_errors_become_memory_unavailable(error: Exception) -> None:
    repo = QdrantMemoryRepository(
        _Broken(error),  # type: ignore[arg-type]
        HashingEmbedder(DIM),
        collection=COLLECTION,
        dimension=DIM,
    )
    calls: list[Any] = [
        repo.index([make_chunk("A", "x")]),
        repo.search("A", "x"),
        repo.similar("A", "id", k=1),
        repo.delete_items("A", ["i"]),
        repo.delete_user("A"),
        repo.vectors("A", limit=1),
    ]
    for call in calls:
        with pytest.raises(VectorStoreUnavailable) as caught:
            await call
        assert caught.value.status_code == 503 and caught.value.code == "memory_unavailable"
        assert "Qdrant" in caught.value.message and "secret-detail" not in caught.value.message
        assert caught.value.__cause__ is None


async def test_embedding_failure_is_not_relabeled_as_vector_store(
    client: AsyncQdrantClient,
) -> None:
    class Down:
        async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
            raise EmbeddingsUnavailable()

        async def aembed_query(self, text: str) -> list[float]:
            raise EmbeddingsUnavailable()

    repo = QdrantMemoryRepository(client, Down(), collection=COLLECTION, dimension=DIM)
    with pytest.raises(EmbeddingsUnavailable):
        await repo.index([make_chunk("A", "x")])
    with pytest.raises(EmbeddingsUnavailable):
        await repo.search("A", "x")

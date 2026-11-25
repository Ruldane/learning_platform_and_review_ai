"""Vector memory port: the `MemoryRepository` interface of the spec (4.1).

It is our own port, implemented with `qdrant-client` and not with LangChain's `VectorStore`: the
map, reindexing and statistics need the raw vectors and the `user_id` filter on each request
(D62)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError

DEFAULT_K = 8


@dataclass(frozen=True)
class ChunkPayload:
    """Copy of the Qdrant payload (spec 4.2) and attachment of the fragment to its item."""

    user_id: str
    kind: str
    item_id: str
    source_id: str | None
    title: str
    text: str
    lang: str | None
    tags: list[str]
    created_by: str
    created_at: str
    session_id: str | None
    ordinal: int


@dataclass(frozen=True)
class ChunkToIndex:
    chunk_id: str
    payload: ChunkPayload


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    score: float
    payload: ChunkPayload


@dataclass(frozen=True)
class VectorRecord:
    chunk_id: str
    vector: list[float]
    payload: ChunkPayload


class VectorStoreUnavailable(AppError):
    """Qdrant unreachable, too slow, or an unexpected response."""

    def __init__(self) -> None:
        super().__init__(
            "memory_unavailable", "The vector database (Qdrant) is unavailable.", status_code=503
        )


class MemoryRepository(Protocol):
    async def index(self, chunks: Sequence[ChunkToIndex]) -> None:
        """Vectorizes (`aembed_documents`), then inserts or replaces; the point id is `chunk_id`."""
        ...

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None = None, k: int = DEFAULT_K
    ) -> list[VectorHit]: ...

    async def similar(
        self, user_id: str, chunk_id: str, *, k: int, exclude_item_id: str | None = None
    ) -> list[VectorHit]: ...

    async def delete_items(self, user_id: str, item_ids: Sequence[str]) -> None: ...

    async def delete_user(self, user_id: str) -> None: ...

    async def vectors(
        self, user_id: str, *, limit: int, item_ids: Sequence[str] | None = None
    ) -> list[VectorRecord]:
        """The user's raw vectors (at most `limit`), restricted to `item_ids` if given."""
        ...

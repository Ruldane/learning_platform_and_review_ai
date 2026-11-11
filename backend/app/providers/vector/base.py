"""Port de la mémoire vectorielle : l'interface `MemoryRepository` de la spec (4.1).

C'est notre port, implémenté avec `qdrant-client` et non avec le `VectorStore` de LangChain : la
carte, la réindexation et les statistiques ont besoin des vecteurs bruts et du filtre `user_id`
sur chaque requête (D62)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError

DEFAULT_K = 8


@dataclass(frozen=True)
class ChunkPayload:
    """Copie du payload Qdrant (spec 4.2) et rattachement du fragment à son élément."""

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
    """Qdrant injoignable, trop lent ou réponse inattendue."""

    def __init__(self) -> None:
        super().__init__(
            "memory_unavailable", "La base vectorielle (Qdrant) est indisponible.", status_code=503
        )


class MemoryRepository(Protocol):
    async def index(self, chunks: Sequence[ChunkToIndex]) -> None:
        """Vectorise (`aembed_documents`) puis insère ou remplace ; l'id du point est `chunk_id`."""
        ...

    async def search(
        self, user_id: str, query: str, *, kinds: Sequence[str] | None = None, k: int = DEFAULT_K
    ) -> list[VectorHit]: ...

    async def similar(
        self, user_id: str, chunk_id: str, *, k: int, exclude_item_id: str | None = None
    ) -> list[VectorHit]: ...

    async def delete_items(self, user_id: str, item_ids: Sequence[str]) -> None: ...

    async def delete_user(self, user_id: str) -> None: ...

    async def vectors(self, user_id: str, *, limit: int) -> list[VectorRecord]: ...

"""Outils des tests du service mémoire : brouillons d'écriture et services externes en panne."""

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from qdrant_client import AsyncQdrantClient

from app.core.providers import MemoryProviders
from app.features.memory.service.rules import WriteDraft
from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.vector.base import (
    ChunkToIndex,
    VectorHit,
    VectorRecord,
    VectorStoreUnavailable,
)
from app.providers.vector.qdrant import QdrantMemoryRepository
from tests.support.memory import FAKE_DIMENSION


def draft(**fields: Any) -> WriteDraft:
    values: dict[str, Any] = {
        "kind": "lecon",
        "title": "Attention",
        "text": "L'attention pondère les mots d'une phrase.",
        "author": "writer",
        "reason": "Leçon publiée.",
        **fields,
    }
    return WriteDraft(**values)


class DownEmbedder:
    """Ollama arrêté ou bge-m3 pas encore téléchargé."""

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingsUnavailable()

    async def aembed_query(self, text: str) -> list[float]:
        raise EmbeddingsUnavailable()


class DownIndex:
    """Qdrant arrêté : chaque appel échoue comme le vrai dépôt."""

    async def index(self, chunks: Sequence[ChunkToIndex]) -> None:
        raise VectorStoreUnavailable()

    async def search(self, user_id: str, query: str, **_: Any) -> list[VectorHit]:
        raise VectorStoreUnavailable()

    async def similar(self, user_id: str, chunk_id: str, **_: Any) -> list[VectorHit]:
        raise VectorStoreUnavailable()

    async def delete_items(self, user_id: str, item_ids: Sequence[str]) -> None:
        raise VectorStoreUnavailable()

    async def delete_user(self, user_id: str) -> None:
        raise VectorStoreUnavailable()

    async def vectors(self, user_id: str, *, limit: int, **_: Any) -> list[VectorRecord]:
        raise VectorStoreUnavailable()


def with_embeddings_down(providers: MemoryProviders) -> MemoryProviders:
    embedder = DownEmbedder()
    index = QdrantMemoryRepository(
        AsyncQdrantClient(location=":memory:"),
        embedder,
        collection="memory",
        dimension=FAKE_DIMENSION,
    )
    return replace(providers, embedder=embedder, index=index)


def with_vector_store_down(providers: MemoryProviders) -> MemoryProviders:
    return replace(providers, index=DownIndex())

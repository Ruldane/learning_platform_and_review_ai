"""Matériel de test de la mémoire : fournisseurs factices (aucun Ollama ni Qdrant réel)."""

import uuid
from pathlib import Path

from qdrant_client import AsyncQdrantClient

from app.core.providers import MemoryProviders
from app.providers.embeddings.fake import HashingEmbedder
from app.providers.vector.base import ChunkPayload, ChunkToIndex
from app.providers.vector.qdrant import QdrantMemoryRepository

FAKE_DIMENSION = 64


def fake_memory_providers(tmp_path: Path) -> MemoryProviders:
    """`HashingEmbedder(64)` et Qdrant en mode local `:memory:` derrière le même port que le vrai.
    `tmp_path` est réservé aux variantes persistantes ; le mode mémoire n'écrit rien."""
    embedder = HashingEmbedder(FAKE_DIMENSION)
    client = AsyncQdrantClient(location=":memory:")
    index = QdrantMemoryRepository(client, embedder, collection="memory", dimension=FAKE_DIMENSION)
    return MemoryProviders(embedder=embedder, index=index)


def make_chunk(
    user: str, text: str, *, kind: str = "acquis", item: str | None = None, ordinal: int = 0
) -> ChunkToIndex:
    """Un fragment à indexer, avec un payload complet et un identifiant frais."""
    item_id = item or str(uuid.uuid4())
    payload = ChunkPayload(
        user_id=user,
        kind=kind,
        item_id=item_id,
        source_id=None,
        title=f"Titre {item_id[:4]}",
        text=text,
        lang="fr",
        tags=["ia"],
        created_by="archiviste",
        created_at="2026-11-11T10:00:00+00:00",
        session_id=None,
        ordinal=ordinal,
    )
    return ChunkToIndex(chunk_id=str(uuid.uuid4()), payload=payload)

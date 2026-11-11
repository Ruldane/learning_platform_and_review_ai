"""Matériel de test de la mémoire : fournisseurs factices (aucun Ollama, Qdrant, YouTube ni
web réel)."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from qdrant_client import AsyncQdrantClient

from app.core.errors import AppError
from app.core.providers import MemoryProviders
from app.providers.embeddings.fake import HashingEmbedder
from app.providers.pdf.extract import PdfPlumberExtractor
from app.providers.storage.local import LocalFileStorage
from app.providers.vector.base import ChunkPayload, ChunkToIndex
from app.providers.vector.qdrant import QdrantMemoryRepository
from app.providers.web.base import Transcript, UrlUnreadable, WebDocument

FAKE_DIMENSION = 64


@dataclass
class FakeWebReader:
    """`pages` : URL → document rendu ou erreur levée ; toute autre URL est illisible."""

    pages: dict[str, WebDocument | AppError] = field(default_factory=dict)
    calls: list[tuple[str, bool]] = field(default_factory=list)

    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        self.calls.append((url, require_text))
        page = self.pages.get(url)
        if page is None:
            raise UrlUnreadable()
        if isinstance(page, AppError):
            raise page
        return page


@dataclass
class FakeYoutube:
    """`videos` : URL → transcription rendue ou erreur levée ; toute autre URL est illisible."""

    videos: dict[str, Transcript | AppError] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    async def transcript(self, url: str) -> Transcript:
        self.calls.append(url)
        video = self.videos.get(url)
        if video is None:
            raise UrlUnreadable()
        if isinstance(video, AppError):
            raise video
        return video


def fake_memory_providers(tmp_path: Path) -> MemoryProviders:
    """`HashingEmbedder(64)` et Qdrant en mode local `:memory:` derrière le même port que le vrai ;
    stockage local réel sous `tmp_path / "storage"`, extracteur PDF réel (local), faux lecteur
    web et faux YouTube."""
    embedder = HashingEmbedder(FAKE_DIMENSION)
    client = AsyncQdrantClient(location=":memory:")
    index = QdrantMemoryRepository(client, embedder, collection="memory", dimension=FAKE_DIMENSION)
    return MemoryProviders(
        embedder=embedder,
        index=index,
        storage=LocalFileStorage(tmp_path / "storage"),
        pdf=PdfPlumberExtractor(),
        web=FakeWebReader(),
        youtube=FakeYoutube(),
    )


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

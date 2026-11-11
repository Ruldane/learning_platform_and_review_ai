"""Indexation d'un élément : fragments en base, vecteurs dans Qdrant. Le texte fait foi en base ;
l'index se reconstruit (D65) : une panne d'Ollama ou de Qdrant laisse l'élément non indexé, sans
erreur pour l'appelant, et la réindexation le rattrape."""

import asyncio
import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.memory import MemoryItem
from app.features.memory.repository import ChunkRepository, MemoryItemRepository
from app.features.memory.service.text import chunk_text
from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.vector.base import (
    ChunkPayload,
    ChunkToIndex,
    MemoryRepository,
    VectorStoreUnavailable,
)

logger = logging.getLogger(__name__)


class MemoryIndexer:
    def __init__(self, index: MemoryRepository) -> None:
        self._index = index
        self._locks: dict[str, asyncio.Lock] = {}
        self._reindexing: set[str] = set()

    def lock(self, user_id: str) -> asyncio.Lock:
        """Verrou de l'utilisateur sur ses vecteurs : une seule écriture dans l'index à la fois
        chez lui. Jamais tenu pendant une attente de SQLite (voir `push`)."""
        return self._locks.setdefault(user_id, asyncio.Lock())

    def reindexing(self, user_id: str) -> bool:
        """Vrai pendant une réindexation de l'utilisateur (posée par la tâche de réindexation)."""
        return user_id in self._reindexing

    async def index_item(self, db: AsyncSession, item: MemoryItem) -> bool:
        """(Ré)indexe l'élément : fragments renouvelés, anciens vecteurs retirés, nouveaux
        insérés. Vrai si l'élément est indexé. Un élément `pending` n'est jamais indexé ; une
        panne d'Ollama ou de Qdrant le laisse non indexé (faux), sans exception."""
        if item.status != "active":
            return False
        chunks = await self.prepare(db, item)
        try:
            await self.push(item.user_id, item.id, chunks)
        except (EmbeddingsUnavailable, VectorStoreUnavailable) as exc:
            logger.warning(
                "Élément %s gardé non indexé (%s), la réindexation le rattrapera",
                item.id,
                type(exc).__name__,
            )
            return False
        await MemoryItemRepository(db, item.user_id).set_indexed_at(item, utcnow())
        return True

    async def prepare(self, db: AsyncSession, item: MemoryItem) -> list[ChunkToIndex]:
        """Première moitié, en base seulement : fragments renouvelés (nouveaux `id`), élément
        marqué non indexé. Le worker la valide (commit) avant `push`, pour ne jamais tenir le
        verrou d'écriture de SQLite pendant la vectorisation. L'appelant a vérifié que l'élément
        appartient à l'utilisateur (`replace_for_item` ne le revérifie pas)."""
        rows = await ChunkRepository(db, item.user_id).replace_for_item(
            item.id, chunk_text(item.text)
        )
        await MemoryItemRepository(db, item.user_id).set_indexed_at(item, None)
        return [ChunkToIndex(row.id, _payload(item, row.ordinal, row.text)) for row in rows]

    async def push(self, user_id: str, item_id: str, chunks: list[ChunkToIndex]) -> None:
        """Seconde moitié, index seulement : tous les vecteurs de l'élément retirés (y compris ceux
        d'un essai interrompu), puis les fragments vectorisés et insérés. Le verrou de
        l'utilisateur ne couvre que ces appels : jamais d'attente de SQLite sous ce verrou.
        Lève `EmbeddingsUnavailable` ou `VectorStoreUnavailable`."""
        async with self.lock(user_id):
            await self._index.delete_items(user_id, [item_id])
            await self._index.index(chunks)

    async def unindex(self, user_id: str, item_ids: Sequence[str]) -> None:
        """Retire les vecteurs ; une panne du magasin est journalisée et avalée (les vecteurs
        orphelins sont écartés à la recherche, la réindexation les purge)."""
        try:
            await self._index.delete_items(user_id, item_ids)
        except VectorStoreUnavailable:
            logger.warning(
                "Vecteurs de %d élément(s) non retirés : magasin indisponible", len(item_ids)
            )


def _payload(item: MemoryItem, ordinal: int, text: str) -> ChunkPayload:
    return ChunkPayload(
        user_id=item.user_id,
        kind=item.kind,
        item_id=item.id,
        source_id=item.source_id,
        title=item.title,
        text=text,
        lang=item.lang,
        tags=[str(tag) for tag in item.tags],
        created_by=item.created_by,
        created_at=item.created_at.isoformat(),
        session_id=item.session_id,
        ordinal=ordinal,
    )

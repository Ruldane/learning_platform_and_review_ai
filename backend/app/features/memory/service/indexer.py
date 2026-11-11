"""Indexation d'un élément : fragments en base, vecteurs dans Qdrant. Le texte fait foi en base ;
l'index se reconstruit (D65) : une panne d'Ollama ou de Qdrant laisse l'élément non indexé, sans
erreur pour l'appelant, et la réindexation le rattrape."""

import asyncio
import logging
from collections import Counter
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


class _Writers:
    """Appels de `index_item` en cours, par utilisateur : leur nombre, une génération qui avance
    à chaque fin d'appel, et un événement levé quand il n'en reste aucun. Tout est synchrone
    (une seule boucle asyncio) : lire puis modifier sans `await` entre les deux est atomique."""

    def __init__(self) -> None:
        self._count: Counter[str] = Counter()
        self._generation: Counter[str] = Counter()
        self._idle: dict[str, asyncio.Event] = {}

    def enter(self, user_id: str) -> None:
        if not self._count[user_id]:
            self._idle[user_id] = asyncio.Event()
        self._count[user_id] += 1

    def leave(self, user_id: str) -> None:
        self._count[user_id] -= 1
        self._generation[user_id] += 1
        if self._count[user_id] <= 0:
            del self._count[user_id]
            self._idle.pop(user_id).set()

    def generation(self, user_id: str) -> int:
        return self._generation[user_id]

    def busy(self, user_id: str) -> bool:
        return self._count[user_id] > 0

    async def drained(self, user_id: str) -> None:
        while self.busy(user_id):
            await self._idle[user_id].wait()


class MemoryIndexer:
    def __init__(self, index: MemoryRepository) -> None:
        self._index = index
        self._locks: dict[str, asyncio.Lock] = {}
        self._reindexing: set[str] = set()
        self._writers = _Writers()

    def lock(self, user_id: str) -> asyncio.Lock:
        """Verrou de l'utilisateur sur ses vecteurs : une seule écriture dans l'index à la fois
        chez lui. Jamais tenu pendant une attente de SQLite (voir `push`)."""
        return self._locks.setdefault(user_id, asyncio.Lock())

    # --- réindexation (D67) : drapeau et écrivains en cours ------------------------------------

    def reindexing(self, user_id: str) -> bool:
        """Vrai pendant une réindexation de l'utilisateur (posée par la tâche de réindexation)."""
        return user_id in self._reindexing

    def begin_reindex(self, user_id: str) -> None:
        self._reindexing.add(user_id)

    def end_reindex(self, user_id: str) -> None:
        self._reindexing.discard(user_id)

    def writers_generation(self, user_id: str) -> int:
        return self._writers.generation(user_id)

    def writers_settled(self, user_id: str, generation: int) -> bool:
        """Aucun `index_item` en cours ni terminé depuis la lecture de `generation`."""
        return not self._writers.busy(user_id) and self._writers.generation(user_id) == generation

    async def wait_writers(self, user_id: str) -> None:
        """Attend la fin des `index_item` en cours. Sans danger : ils n'attendent jamais celui
        qui appelle (la réindexation ne tient ni transaction ni verrou en attendant)."""
        await self._writers.drained(user_id)

    # --- indexation ------------------------------------------------------------------------------

    async def index_item(self, db: AsyncSession, item: MemoryItem) -> bool:
        """(Ré)indexe l'élément : fragments renouvelés, anciens vecteurs retirés, nouveaux
        insérés. Vrai si l'élément est indexé. Un élément `pending` n'est jamais indexé ; une
        panne d'Ollama ou de Qdrant le laisse non indexé (faux), sans exception.

        **Valide la transaction de l'appelant** (D66) avant la vectorisation, comme le worker :
        le verrou d'écriture de SQLite n'est jamais tenu pendant l'appel à Ollama ni pendant
        l'attente du verrou de l'utilisateur. `indexed_at` est ensuite posé par une seconde
        transaction courte. Une panne après le premier commit laisse l'élément enregistré,
        lisible et non indexé : la réindexation le rattrapera.

        Pendant une réindexation de l'utilisateur (D67), les fragments sont renouvelés et
        validés mais l'index n'est pas touché : l'élément reste non indexé (faux) et la boucle de
        réindexation le rattrape. Le drapeau est lu sans `await` avant de se compter parmi les
        écrivains en cours : une réindexation qui démarre après attend la fin de cet appel."""
        if item.status != "active":
            return False
        user_id = item.user_id
        deferred = self.reindexing(user_id)
        self._writers.enter(user_id)
        try:
            chunks = await self.prepare(db, item)
            await db.commit()
            if deferred:
                logger.info("Élément %s laissé à la réindexation en cours", item.id)
                return False
            try:
                await self.push(user_id, item.id, chunks)
            except (EmbeddingsUnavailable, VectorStoreUnavailable) as exc:
                logger.warning(
                    "Élément %s gardé non indexé (%s), la réindexation le rattrapera",
                    item.id,
                    type(exc).__name__,
                )
                return False
            return await self.mark_indexed(db, user_id, [(item, chunks)]) == 1
        finally:
            self._writers.leave(user_id)

    async def mark_indexed(
        self,
        db: AsyncSession,
        user_id: str,
        pushed: Sequence[tuple[MemoryItem, list[ChunkToIndex]]],
    ) -> int:
        """Après `push`, transaction courte validée ici : `indexed_at` posé pour chaque élément
        dont les fragments poussés sont toujours en base (sinon une écriture concurrente les a
        renouvelés : il reste non indexé, à rattraper). Les vecteurs d'un élément supprimé
        pendant `push` sont retirés après le commit. Rend le nombre d'éléments marqués."""
        repo = MemoryItemRepository(db, user_id)
        at, marked, gone = utcnow(), 0, []
        for item, chunks in pushed:
            if await repo.mark_indexed(item, at, chunks[0].chunk_id if chunks else None):
                marked += 1
            elif await repo.get(item.id) is None:
                gone.append(item.id)
        await db.commit()
        if gone:
            await self.unindex(user_id, gone)
        return marked

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

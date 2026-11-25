"""Indexing an item: chunks in the database, vectors in Qdrant. The text is authoritative in
the database; the index can be rebuilt (D65): an Ollama or Qdrant outage leaves the item
unindexed, without error for the caller, and the reindexing catches it up."""

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
    """`index_item` calls in progress, per user: their number, a generation that advances at
    each end of call, and an event raised when none remains. Everything is synchronous (a
    single asyncio loop): reading then modifying without an `await` between the two is atomic."""

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
        self._retired_users: set[str] = set()
        self._writers = _Writers()

    def lock(self, user_id: str) -> asyncio.Lock:
        """The user's lock on their vectors: a single write to the index at a time for them.
        Never held while waiting on SQLite (see `push`)."""
        return self._locks.setdefault(user_id, asyncio.Lock())

    # --- reindexing (D67): flag and writers in progress ---------------------------------------

    def reindexing(self, user_id: str) -> bool:
        """True during a reindexing of the user (set by the reindexing task)."""
        return user_id in self._reindexing

    def begin_reindex(self, user_id: str) -> None:
        self._reindexing.add(user_id)

    def end_reindex(self, user_id: str) -> None:
        self._reindexing.discard(user_id)

    def writers_generation(self, user_id: str) -> int:
        return self._writers.generation(user_id)

    def writers_settled(self, user_id: str, generation: int) -> bool:
        """No `index_item` in progress or finished since the reading of `generation`."""
        return not self._writers.busy(user_id) and self._writers.generation(user_id) == generation

    async def wait_writers(self, user_id: str) -> None:
        """Waits for the `index_item` calls in progress to end. Safe: they never wait for the
        caller (the reindexing holds neither a transaction nor a lock while waiting)."""
        await self._writers.drained(user_id)

    # --- indexation ------------------------------------------------------------------------------

    async def index_item(self, db: AsyncSession, item: MemoryItem) -> bool:
        """(Re)indexes the item: chunks renewed, old vectors removed, new ones inserted. True if
        the item is indexed. A `pending` item is never indexed; an Ollama or Qdrant outage
        leaves it unindexed (false), without an exception.

        **Commits the caller's transaction** (D66) before vectorizing, like the worker:
        SQLite's write lock is never held during the call to Ollama nor while waiting for the
        user's lock. `indexed_at` is then set by a second short transaction. A failure after
        the first commit leaves the item stored, readable and unindexed: the reindexing will
        catch it up.

        During a reindexing of the user (D67), the chunks are renewed and committed but the
        index is not touched: the item stays unindexed (false) and the reindexing loop catches
        it up. The flag is read without an `await` before counting oneself among the writers in
        progress: a reindexing that starts afterwards waits for the end of this call."""
        if item.status != "active":
            return False
        user_id = item.user_id
        deferred = self.reindexing(user_id)
        self._writers.enter(user_id)
        try:
            chunks = await self.prepare(db, item)
            await db.commit()
            if deferred:
                logger.info("Item %s left to the reindexing in progress", item.id)
                return False
            try:
                await self.push(user_id, item.id, chunks)
            except (EmbeddingsUnavailable, VectorStoreUnavailable) as exc:
                logger.warning(
                    "Item %s kept unindexed (%s), the reindexing will catch it up",
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
        """After `push`, short transaction committed here: `indexed_at` set for each item whose
        pushed chunks are still in the database (otherwise a concurrent write renewed them: it
        stays unindexed, to be caught up). The vectors of an item deleted during `push` are
        removed after the commit. Returns the number of items marked."""
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
        """First half, in the database only: chunks renewed (new `id`s), item marked unindexed.
        The worker commits it before `push`, to never hold SQLite's write lock during
        vectorization. The caller checked that the item belongs to the user
        (`replace_for_item` does not re-check)."""
        rows = await ChunkRepository(db, item.user_id).replace_for_item(
            item.id, chunk_text(item.text)
        )
        await MemoryItemRepository(db, item.user_id).set_indexed_at(item, None)
        return [ChunkToIndex(row.id, _payload(item, row.ordinal, row.text)) for row in rows]

    async def push(self, user_id: str, item_id: str, chunks: list[ChunkToIndex]) -> None:
        """Second half, index only: all the item's vectors removed (including those of an
        interrupted attempt), then the vectorized chunks inserted. The user's lock only covers
        these calls: never waiting on SQLite under this lock. Raises `EmbeddingsUnavailable` or
        `VectorStoreUnavailable`."""
        async with self.lock(user_id):
            if user_id in self._retired_users:
                return
            await self._index.delete_items(user_id, [item_id])
            await self._index.index(chunks)

    async def purge_retired_user(self, user_id: str) -> None:
        """Closes the indexing of a deleted Google account for good. Waits for any write under
        the lock, then erases its vectors. A recreated account has another id."""
        self._retired_users.add(user_id)
        async with self.lock(user_id):
            await self._index.delete_user(user_id)

    async def unindex(self, user_id: str, item_ids: Sequence[str]) -> None:
        """Removes the vectors; a store outage is logged and swallowed (orphan vectors are
        discarded at search time, the reindexing purges them)."""
        try:
            await self._index.delete_items(user_id, item_ids)
        except VectorStoreUnavailable:
            logger.warning("Vectors of %d item(s) not removed: store unavailable", len(item_ids))


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

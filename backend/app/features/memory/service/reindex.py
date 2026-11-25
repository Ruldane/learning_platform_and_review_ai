"""Reindexing of a user's memory (4.6, D67): the Qdrant index is rebuilt from the text, which
is authoritative in the database; chunks are recomputed along the way. Run by the worker
(`jobs.py`), serially with imports: no import runs at the same time.

Never an open SQLite transaction during an Ollama or Qdrant call, never the user's asyncio
lock held while waiting on SQLite (D66):

1. `reindexing` flag raised: an `index_item` starting afterwards renews its chunks without
   touching the index and leaves the item unindexed; those already started are awaited;
2. Ollama and Qdrant probed (an outage stops everything before any deletion), then
   `clear_indexed` (short transaction), then `delete_user` under the user's lock;
3. in batches of 16: chunks prepared and committed, pushed (lock taken and released per item
   in `push`), then `indexed_at` set if the chunks have not changed in the meantime;
4. end when a batch is empty and no writer has acted since it was read: the flag is lowered
   in the same synchronous step. Ollama or Qdrant outage: the port's error propagates
   (readable message), the remaining items keep a null `indexed_at`.

Logs only mention identifiers and numbers."""

import logging
from collections.abc import Callable

from app.features.memory.repository import MemoryItemRepository
from app.features.memory.schemas import ReindexState
from app.features.memory.service.runtime import MemoryRuntime

logger = logging.getLogger(__name__)

BATCH_SIZE = 16

Report = Callable[[ReindexState], None]


def running(done: int, total: int) -> ReindexState:
    return ReindexState(status="running", done=done, total=max(total, done), error=None)


async def reindex_user(runtime: MemoryRuntime, user_id: str, report: Report) -> None:
    """Rebuilds the user's index and reports progress (`report`); the final `done` state is
    reported here. An outage raises the port's error: the caller reports it."""
    indexer = runtime.indexer
    indexer.begin_reindex(user_id)
    try:
        total = await _reset(runtime, user_id)
        report(running(0, total))
        done = await _rebuild(runtime, user_id, total, report)
    finally:
        indexer.end_reindex(user_id)
    report(ReindexState(status="done", done=done, total=max(total, done), error=None))
    logger.info("Reindexing of %s finished: %d item(s)", user_id, done)


async def _reset(runtime: MemoryRuntime, user_id: str) -> int:
    """Steps 1 and 2: running writers finished, everything marked for reindexing, vectors
    deleted. Returns the number of items to reindex. Ollama and Qdrant are probed before any
    deletion (outside any transaction or lock): on an outage, the port's error propagates and
    the existing index stays intact."""
    await runtime.indexer.wait_writers(user_id)
    await runtime.providers.embedder.aembed_query("ping")
    await runtime.providers.index.vectors(user_id, limit=1)
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, user_id)
        await items.clear_indexed()
        await db.commit()
        total = await items.count_unindexed()
        await db.commit()
    async with runtime.indexer.lock(user_id):
        await runtime.providers.index.delete_user(user_id)
    return total


async def _rebuild(runtime: MemoryRuntime, user_id: str, total: int, report: Report) -> int:
    """Steps 3 and 4: batches until exhausted. Returns the number of indexed items."""
    indexer, done = runtime.indexer, 0
    while True:
        generation = indexer.writers_generation(user_id)
        marked, read = await _batch(runtime, user_id)
        if read:
            done += marked
            report(running(done, total))
            continue
        if indexer.writers_settled(user_id, generation):
            indexer.end_reindex(user_id)  # no `await` since the check: nothing could slip in
            return done
        await indexer.wait_writers(user_id)


async def _batch(runtime: MemoryRuntime, user_id: str) -> tuple[int, int]:
    """One batch: `(items marked indexed, items read)`. SQLite's write lock is taken before
    the read (no read → write upgrade rejected by SQLite) and released before embedding."""
    indexer = runtime.indexer
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, user_id)
        await items.begin_write()
        batch = await items.unindexed_batch(BATCH_SIZE)
        prepared = [(item, await indexer.prepare(db, item)) for item in batch]
        await db.commit()
        for item, chunks in prepared:
            await indexer.push(user_id, item.id, chunks)
        marked = await indexer.mark_indexed(db, user_id, prepared) if prepared else 0
    return marked, len(batch)

"""Memory items written directly by a feature that has no agent behind it (phase 10, 10.W): the
lesson or offer that Claude (through MCP) or January writes itself. Same write as the agents'
(rules, deduplication, journal), without agent gateway or session.

**The call does not index.** The item is written (or updated) in the feature's transaction,
with `indexed_at` empty, and indexing (fragments, embeddings, Qdrant) follows outside the call:
`schedule_indexing` starts it after the response, the MCP undo restarts it, and the maintenance
task catches up after a restart (`index_pending_all`). Reason: the MCP history only removes
what it has seen; indexing within the call would set `indexed_at` and replace fragments through
bulk queries, which the undo could not reverse. A rewrite therefore does not touch the
fragments: it resets `indexed_at` to empty, and the undo does the same (`app.mcp.undo`).

A vector of an item removed by the undo stays in Qdrant until the next re-indexing; search
discards any vector with no fragment or item in the database. No model call: embeddings only."""

import asyncio
import contextvars
import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import USER_AUTHOR, MemoryItem, MemoryKind
from app.features.memory.repository import (
    MemoryItemRepository,
    WriteRepository,
    users_with_unindexed,
)
from app.features.memory.schemas import MemoryItemPatch
from app.features.memory.service.items import MemoryService, _content
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import content_hash

logger = logging.getLogger(__name__)

__all__ = [
    "author_of",
    "drain_indexing",
    "index_pending",
    "index_pending_all",
    "schedule_indexing",
    "write_direct",
]

MCP_AUTHOR = "claude"
BATCH = 16  # items indexed per pass, per user
USERS = 20  # users seen per pass of the maintenance task
_TASKS: set["asyncio.Task[None]"] = set()
_paused = False  # test hook: `schedule_indexing` starts nothing (state "before indexing")


def author_of(is_mcp: bool) -> str:
    """`claude` when the call comes from MCP, `user` otherwise (the interface)."""
    return MCP_AUTHOR if is_mcp else USER_AUTHOR


async def _retouch(
    service: MemoryService,
    db: AsyncSession,
    user_id: str,
    kind: MemoryKind,
    old: tuple[str, str],
    new: tuple[str, str],
    tags: Sequence[str],
    author: str,
    reason: str,
) -> MemoryItem | None:
    """The item that held `old` (title, text), updated with `new` and to be re-indexed; `None` if
    there is none. Its fragments are not touched (see the module)."""
    previous = await MemoryItemRepository(db, user_id).find_by_hash(
        content_hash(kind, *_content(*old))
    )
    if previous is None:
        return None
    patch = MemoryItemPatch.model_construct(title=new[0], text=new[1], tags=list(tags))
    if await service._edit(previous, patch):  # noqa: SLF001 - same package: the rewrite rule
        previous.indexed_at = None
        await WriteRepository(db, user_id).log(
            item=previous, action="update", author=author, session_id=None, reason=reason
        )
    return previous


async def write_direct(
    db: AsyncSession,
    runtime: MemoryRuntime,
    user_id: str,
    *,
    kind: MemoryKind,
    title: str,
    text: str,
    tags: Sequence[str],
    author: str,
    reason: str,
    replaces: tuple[str, str] | None = None,
    session_id: str | None = None,
) -> str:
    """Writes the item, or updates the one that held `replaces` (title, text), within the caller's
    transaction (no commit: all or nothing with the feature's row). Returns its identifier. A
    memory error propagates (`AppError`: code, never the content) and undoes the whole write. The
    caller starts `schedule_indexing` after its commit."""
    service = MemoryService(db, user_id, runtime)
    item = None
    if replaces is not None:
        item = await _retouch(
            service, db, user_id, kind, replaces, (title, text), tags, author, reason
        )
    if item is None:
        draft = WriteDraft(
            kind=kind,
            title=title,
            text=text,
            author=author,
            reason=reason,
            tags=tuple(tags),
            session_id=session_id,
        )
        item = (await service.write(draft, index=False)).item
    return item.id


async def index_pending(runtime: MemoryRuntime, user_id: str, limit: int = BATCH) -> int:
    """Indexes the user's active items still at empty `indexed_at` (at most `limit`); returns the
    number indexed. Stops at the first failure (Ollama or Qdrant stopped, re-indexing in progress):
    the next pass resumes. One item at a time, each in its own session."""
    async with runtime.session_factory() as db:
        ids = [item.id for item in await MemoryItemRepository(db, user_id).unindexed_batch(limit)]
    done = 0
    for item_id in ids:
        async with runtime.session_factory() as db:
            item = await MemoryItemRepository(db, user_id).get(item_id)
            if item is None or item.indexed_at is not None:
                continue
            if not await runtime.indexer.index_item(db, item):
                break
        done += 1
    return done


async def index_pending_all(runtime: MemoryRuntime) -> int:
    """One pass of the maintenance task: `index_pending` for each account that has items to index
    (at most `USERS`). A failure is logged (its type) and moves on to the next account."""
    async with runtime.session_factory() as db:
        users = await users_with_unindexed(db, USERS)
    total = 0
    for user_id in users:
        try:
            total += await index_pending(runtime, user_id)
        except Exception as exc:
            logger.warning("Indexation en attente non faite (%s)", type(exc).__name__)
    return total


async def _safely(runtime: MemoryRuntime, user_id: str) -> None:
    try:
        await index_pending(runtime, user_id)
    except Exception as exc:  # the maintenance task will resume
        logger.warning("Indexation en attente non faite (%s)", type(exc).__name__)


def schedule_indexing(runtime: MemoryRuntime, user_id: str) -> None:
    """Starts `index_pending` as a background task, after the response. It starts from an empty
    context: neither the MCP history nor the call's identity sees it (it only writes indexing)."""
    if _paused:
        return
    task = asyncio.get_running_loop().create_task(
        _safely(runtime, user_id), context=contextvars.Context()
    )
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


async def drain_indexing() -> None:
    """Waits for the started indexing runs (tests, clean shutdown)."""
    while _TASKS:
        await asyncio.gather(*list(_TASKS), return_exceptions=True)

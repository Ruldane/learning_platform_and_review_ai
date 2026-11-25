"""Database steps of the ingestion chain (`pipeline.py`), each a short transaction.

The final writes (`finish`, `mark_error`) are replayed at most twice if SQLite refuses the
write lock ("database is locked" after the 5 s of `busy_timeout`): a lost final status would
leave the document `processing` until the next start."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.memory import USER_AUTHOR, Document, MemoryItem
from app.features.memory.repository import (
    DocumentRepository,
    MemoryItemRepository,
    WriteRepository,
)
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.sources.base import SourceInput
from app.features.memory.service.text import clean_display, content_hash
from app.providers.vector.base import ChunkToIndex, VectorStoreUnavailable

logger = logging.getLogger(__name__)

RESUMABLE = ("queued", "processing")
RETRIES = 2
RETRY_BACKOFF_S = 0.2
_RENAMED_BY_TITLE = ("url", "youtube")


@dataclass(frozen=True)
class Claim:
    source: SourceInput
    kind: str


@dataclass(frozen=True)
class Written:
    item_id: str
    chunks: list[ChunkToIndex] | None  # None: already indexed, nothing to push


class Gone(Exception):
    """The document disappeared during the import (deleted with its item)."""


def error_of(exc: AppError) -> dict[str, Any]:
    """`{code, message}` of a business error (constant messages, without received content); the
    existing item of a duplicate is kept (`item_id`)."""
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details and "item_id" in exc.details:
        error["item_id"] = exc.details["item_id"]
    return error


def duplicate_content(item_id: str) -> AppError:
    return AppError(
        "duplicate_content", "This content is already in memory.", 409, details={"item_id": item_id}
    )


async def with_retry[**P](
    step: Callable[P, Awaitable[None]], *args: P.args, **kwargs: P.kwargs
) -> None:
    for attempt in range(RETRIES + 1):
        try:
            await step(*args, **kwargs)
            return
        except OperationalError as exc:
            if attempt == RETRIES:
                raise
            logger.warning("Write refused by SQLite (%s), retrying", type(exc).__name__)
            await asyncio.sleep(RETRY_BACKOFF_S * (attempt + 1))


async def claim(runtime: MemoryRuntime, user_id: str, document_id: str) -> Claim | None:
    """The document becomes `processing`; `None` if it is not found or already handled."""
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.status not in RESUMABLE:
            return None
        doc.status = "processing"
        await db.commit()
        return Claim(
            SourceInput(
                doc.id,
                user_id,
                doc.name,
                doc.url,
                doc.storage_key,
                tuple(map(str, doc.tags)),
                doc.sync_metadata,
            ),
            doc.source_kind,
        )


async def write_item(
    runtime: MemoryRuntime, claim: Claim, title: str, text: str, lang: str | None
) -> Written:
    """`document` item and its chunks, committed before any vectorization. The write lock is
    taken first: a document deleted meanwhile stops the import. The document already has its
    item (resume, re-read of a link): that item is updated, never doubled."""
    src = claim.source
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, src.user_id)
        await items.begin_write()
        if await DocumentRepository(db, src.user_id).get(src.document_id) is None:
            raise Gone()
        own = await items.find_document_of(src.document_id)
        if own is None:
            item, changed = await _create(db, runtime, src, title, text, lang)
        else:
            item, changed = await _refresh(db, src, own, title, text, lang)
        chunks = None
        if changed or item.indexed_at is None:
            chunks = await runtime.indexer.prepare(db, item)
        await DocumentRepository(db, src.user_id).update(src.document_id, item_id=item.id)
        await db.commit()
        return Written(item.id, chunks)


async def _create(
    db: AsyncSession,
    runtime: MemoryRuntime,
    src: SourceInput,
    title: str,
    text: str,
    lang: str | None,
) -> tuple[MemoryItem, bool]:
    draft = WriteDraft(
        kind="document",
        title=title,
        text=text,
        author=USER_AUTHOR,
        reason=(
            "Import of a synced note."
            if src.sync_metadata is not None
            else f"Import of the document '{src.name}'."
        ),
        source_id=src.document_id,
        lang=lang,
        tags=src.tags,
        sync_metadata=src.sync_metadata,
    )
    outcome = await MemoryService(db, src.user_id, runtime).write(draft, index=False)
    if not outcome.created and outcome.item.source_id != src.document_id:
        raise duplicate_content(outcome.item.id)
    return outcome.item, outcome.created


async def _refresh(
    db: AsyncSession, src: SourceInput, own: MemoryItem, title: str, text: str, lang: str | None
) -> tuple[MemoryItem, bool]:
    """New content for the document's item (page modified between two reads). The write lock is
    held: no concurrent insertion of the same hash is possible."""
    document_id = src.document_id if src.sync_metadata is not None else None
    digest = content_hash("document", title, text, document_id=document_id)
    if digest == own.content_hash:
        return own, False
    clash = await MemoryItemRepository(db, src.user_id).find_by_hash(digest)
    if clash is not None:
        raise duplicate_content(clash.id)
    own.title, own.text, own.content_hash, own.lang = title, text, digest, lang
    await db.flush()
    await WriteRepository(db, src.user_id).log(
        item=own,
        action="update",
        author=USER_AUTHOR,
        session_id=None,
        reason=(
            "Re-read of a synced note."
            if src.sync_metadata is not None
            else f"Re-read of the document '{src.name}'."
        ),
    )
    return own, True


async def finish_once(
    runtime: MemoryRuntime, claim: Claim, written: Written, title: str, failure: AppError | None
) -> None:
    """Final status: `indexed`, or `error` with the failing provider's message (the item is
    kept unindexed: the reindexing will catch it up). The write lock is taken before the
    reads: the document and the item can no longer disappear before the commit. Item deleted
    during `push`: the vectors pushed after its deletion are removed once the transaction is
    closed (M2, D71). Only the document gone (the item remains): nothing is removed, the item
    already marked unindexed by `prepare` will be caught up by the reindexing."""
    src = claim.source
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, src.user_id)
        await items.begin_write()
        doc = await DocumentRepository(db, src.user_id).get(src.document_id)
        item = await items.get(written.item_id)
        if doc is None or item is None:
            await db.rollback()  # deleted meanwhile (the item takes the document with it)
        else:
            await _settle(items, doc, item, claim, written, title, failure)
            await db.commit()
    if item is None and written.chunks is not None:
        await drop_orphan_vectors(runtime, src.user_id, written.item_id)
    if doc is None or item is None:
        return
    if failure is None:
        logger.info("Document %s indexed (item %s)", src.document_id, written.item_id)
    else:
        logger.info("Document %s failed (%s)", src.document_id, failure.code)


async def _settle(
    items: MemoryItemRepository,
    doc: Document,
    item: MemoryItem,
    claim: Claim,
    written: Written,
    title: str,
    failure: AppError | None,
) -> None:
    if failure is None and written.chunks is not None:
        # Conditional (D67): chunks renewed meanwhile (modification during `push`) leave the
        # item to be caught up instead of wrongly calling it indexed.
        first = written.chunks[0].chunk_id if written.chunks else None
        await items.mark_indexed(item, utcnow(), first)
    if claim.kind in _RENAMED_BY_TITLE and clean_display(title):
        doc.name = clean_display(title)  # title from the site: cleaned like a received name
    doc.item_id = written.item_id
    if failure is None:
        doc.status, doc.error = "indexed", None
    else:
        doc.status, doc.error = "error", error_of(failure)


async def drop_orphan_vectors(runtime: MemoryRuntime, user_id: str, item_id: str) -> None:
    """Removes the vectors of an item deleted during its import, outside any transaction; a
    store outage is swallowed and logged by id (the reindexing purges the remaining orphans,
    the search already discards them)."""
    try:
        await runtime.providers.index.delete_items(user_id, [item_id])
    except VectorStoreUnavailable:
        logger.warning("Orphan vectors of item %s not removed: store unavailable", item_id)
        return
    logger.info("Orphan vectors of item %s removed (deleted during the import)", item_id)


async def finish(
    runtime: MemoryRuntime, claim: Claim, written: Written, title: str, failure: AppError | None
) -> None:
    await with_retry(finish_once, runtime, claim, written, title, failure)


async def mark_error_once(
    runtime: MemoryRuntime, user_id: str, document_id: str, error: dict[str, Any]
) -> None:
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.status not in RESUMABLE:
            return
        doc.status, doc.error = "error", error
        await db.commit()
    logger.info("Document %s failed (%s)", document_id, error["code"])


async def mark_error(
    runtime: MemoryRuntime, user_id: str, document_id: str, error: dict[str, Any]
) -> None:
    """Status `error` for a document still queued or running (otherwise nothing)."""
    await with_retry(mark_error_once, runtime, user_id, document_id, error)

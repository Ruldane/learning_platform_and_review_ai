"""Reading, writing and indexing of memory items.
The commit belongs to the request, except to index and delete a document (D66)."""

from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.memory import USER_AUTHOR, MemoryItem, MemoryKind, WriteAction
from app.features.memory.repository import (
    ChunkRepository,
    ItemFilter,
    MemoryItemRepository,
    WriteRepository,
)
from app.features.memory.schemas import (
    ChunkOut,
    MemoryItemCreate,
    MemoryItemDetail,
    MemoryItemList,
    MemoryItemOut,
    MemoryItemPatch,
    MemoryWriteOut,
    NeighborOut,
)
from app.features.memory.service.documents import DocumentService
from app.features.memory.service.linked_notes import linked_notes
from app.features.memory.service.rules import WriteDraft, clean_tags, resolve_write
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import clean_text, content_hash
from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.vector.base import VectorStoreUnavailable

__all__ = ["ItemFilter", "MemoryService", "WriteOutcome", "to_out"]

TITLE_MAX = 200
NEIGHBORS = 5


@dataclass(frozen=True)
class WriteOutcome:
    item: MemoryItem
    created: bool


def not_found() -> AppError:
    return AppError("memory_item_not_found", "Memory item not found.", 404)


def duplicate() -> AppError:
    return AppError("memory_duplicate", "An identical item already exists.", 409)


def _content(title: str, text: str) -> tuple[str, str]:
    """Title and text cleaned; neither can be empty."""
    title, text = title.strip()[:TITLE_MAX], clean_text(text)
    if not title or not text:
        raise AppError("memory_content_required", "Enter both a title and some text.", 422)
    return title, text


def to_out(item: MemoryItem) -> MemoryItemOut:
    meta = item.meta or {}
    return MemoryItemOut.model_validate(
        {
            "id": item.id,
            "kind": item.kind,
            "title": item.title,
            "text": item.text,
            "tags": [str(tag) for tag in item.tags],
            "created_by": item.created_by,
            "session_id": item.session_id,
            "source_id": item.source_id,
            "lang": item.lang,
            "status": item.status,
            "level": meta.get("level"),
            "evidence": [str(e) for e in meta.get("evidence", [])],
            "reason": meta.get("reason"),
            "indexed": item.indexed_at is not None,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
    )


class MemoryService:
    def __init__(self, db: AsyncSession, user_id: str, runtime: MemoryRuntime) -> None:
        self.db, self.user_id, self.runtime = db, user_id, runtime  # read by `merge.py`
        self._items = MemoryItemRepository(db, user_id)
        self._chunks = ChunkRepository(db, user_id)
        self._writes = WriteRepository(db, user_id)

    async def get(self, item_id: str) -> MemoryItem:
        """User's item or 404. Every modification goes through here: the fragments
        (`replace_for_item`) and the index do not re-check the owner."""
        item = await self._items.get(item_id)
        if item is None:
            raise not_found()
        return item

    # --- write ---------------------------------------------------------------------------------

    async def write(self, draft: WriteDraft, *, index: bool = True) -> WriteOutcome:
        """Writes an item according to the rules (`resolve_write`). Same content already there:
        returns the existing item without a second item or a second journal entry (agent node
        replayed, double click). Two simultaneous writes: the loser re-reads the winner. Active:
        indexed immediately, unless `index=False` (the worker indexes after validating its
        transaction)."""
        status, meta = resolve_write(draft)
        title, text = _content(draft.title, draft.text)
        document_id = draft.source_id if draft.sync_metadata is not None else None
        digest = content_hash(draft.kind, title, text, document_id=document_id)
        if draft.sync_metadata is not None:
            meta["sync_metadata"] = draft.sync_metadata
        existing = await self._items.find_by_hash(digest)
        if existing is not None:
            return WriteOutcome(existing, False)
        fields: dict[str, Any] = {
            "kind": draft.kind,
            "title": title,
            "text": text,
            "tags": clean_tags(draft.tags),
            "created_by": draft.author,
            "session_id": draft.session_id,
            "source_id": draft.source_id,
            "lang": draft.lang,
            "status": status,
            "meta": meta,
            "content_hash": digest,
        }
        item, created = await self._insert(fields, digest)
        if not created:
            return WriteOutcome(item, False)
        reason = (draft.reason or "").strip() or None
        await self._writes.log(
            item=item,
            action="create",
            author=draft.author,
            session_id=draft.session_id,
            reason=reason,
        )
        if index and item.status == "active":
            await self.runtime.indexer.index_item(self.db, item)
        return WriteOutcome(item, True)

    async def _insert(self, fields: dict[str, Any], digest: str) -> tuple[MemoryItem, bool]:
        """Insert under SAVEPOINT: the uniqueness of the hash decides a race; the loser re-reads."""
        await self._items.begin_write()
        try:
            async with self.db.begin_nested():
                return await self._items.add(**fields), True
        except IntegrityError:
            winner = await self._items.find_by_hash(digest)
            if winner is None:
                raise
            return winner, False

    async def create_by_user(self, body: MemoryItemCreate) -> MemoryItemOut:
        """Item written by hand (January): active immediately, logged with author `user`. Content
        already present returns the existing item."""
        outcome = await self.write(
            WriteDraft(
                kind=body.kind,
                title=body.title,
                text=body.text,
                author=USER_AUTHOR,
                reason=None,
                tags=tuple(body.tags),
                level=body.level,
            )
        )
        return to_out(outcome.item)

    # --- lecture ----------------------------------------------------------------------------

    async def list_items(self, f: ItemFilter, *, limit: int, offset: int) -> MemoryItemList:
        rows, total = await self._items.filtered(f, limit=limit, offset=offset)
        return MemoryItemList(items=[to_out(row) for row in rows], total=total)

    async def detail(self, item_id: str) -> MemoryItemDetail:
        item = await self.get(item_id)
        chunks = await self._chunks.for_item(item.id)
        writes = await self._writes.for_item(item.id)
        return MemoryItemDetail(
            **to_out(item).model_dump(),
            chunks=[ChunkOut.model_validate(c, from_attributes=True) for c in chunks],
            neighbors=await self._neighbors(item, chunks[0].id if chunks else None),
            writes=[MemoryWriteOut.model_validate(w, from_attributes=True) for w in writes],
            linked_notes=await linked_notes(self.db, item),
        )

    async def _neighbors(self, item: MemoryItem, first_chunk_id: str | None) -> list[NeighborOut]:
        """Neighbouring items of the first fragment (one per item, the closest). Index down or item
        not indexed: no neighbours, never an error. Titles re-read from the database."""
        if first_chunk_id is None or item.indexed_at is None:
            return []
        try:
            hits = await self.runtime.providers.index.similar(
                self.user_id, first_chunk_id, k=NEIGHBORS, exclude_item_id=item.id
            )
        except (EmbeddingsUnavailable, VectorStoreUnavailable):
            return []
        best: dict[str, float] = {}
        for hit in hits:
            best.setdefault(hit.payload.item_id, hit.score)
        rows = await self._items.get_many(list(best))
        return [
            NeighborOut.model_validate(
                {
                    "item_id": rows[item_id].id,
                    "title": rows[item_id].title,
                    "kind": rows[item_id].kind,
                    "score": min(score, 1.0),
                }
            )
            for item_id, score in best.items()
            if item_id in rows and rows[item_id].status == "active"
        ]

    # --- modification -----------------------------------------------------------------------

    async def update(self, item_id: str, patch: MemoryItemPatch) -> MemoryItemOut:
        """Title, text, labels, level (acquired only) and confirmation. Modified content gets a new
        hash (409 if it already exists), is re-indexed and logged `update`; confirming a pending
        decision makes it active, indexes it and logs `confirm`."""
        item = await self.get(item_id)
        if patch.level is not None and item.kind != "skill":
            raise AppError("memory_level_forbidden", "Only skills have a level.", 422)
        content = await self._edit(item, patch)
        level = patch.level is not None and item.meta.get("level") != patch.level
        if level:
            item.meta = {**item.meta, "level": patch.level}
        confirmed = patch.status == "active" and item.status == "pending"
        if confirmed:
            item.status = "active"
        await self.db.flush()
        if content or level:
            await self._log(item, "update")
        if confirmed:
            await self._log(item, "confirm")
        if item.status == "active" and (content or confirmed):
            await self.runtime.indexer.index_item(self.db, item)
        return to_out(item)

    async def _edit(self, item: MemoryItem, patch: MemoryItemPatch) -> bool:
        """Applies title, text and labels; true if one changed. Content that collides with another
        item (same hash) is refused."""
        title, text = _content(
            item.title if patch.title is None else patch.title,
            item.text if patch.text is None else patch.text,
        )
        tags = list(item.tags) if patch.tags is None else clean_tags(patch.tags)
        if (title, text, tags) == (item.title, item.text, list(item.tags)):
            return False
        document_id = item.source_id if "sync_metadata" in item.meta else None
        digest = content_hash(cast(MemoryKind, item.kind), title, text, document_id=document_id)
        clash = await self._items.find_by_hash(digest)
        if clash is not None and clash.id != item.id:
            raise duplicate()
        await self._items.begin_write()
        try:
            async with self.db.begin_nested():
                item.title, item.text, item.tags, item.content_hash = title, text, tags, digest
                await self.db.flush()
        except IntegrityError:
            raise duplicate() from None
        return True

    async def _log(self, item: MemoryItem, action: WriteAction) -> None:
        await self._writes.log(
            item=item,
            action=action,
            author=USER_AUTHOR,
            session_id=None,
            reason=None,
        )

    async def delete(self, item_id: str) -> None:
        """Deletes the item, its fragments (cascade) and its vectors. A pending decision that is
        refused is logged `reject`, the rest `delete`. A document also loses its `documents` rows,
        and their files after the commit (never a row without its file). **Validates the
        transaction** before removing the vectors, outside the transaction (D66)."""
        item = await self.get(item_id)
        keys: list[str] = []
        if item.kind == "document":
            docs = DocumentService(self.db, self.user_id, self.runtime)
            keys = await docs.remove_for_item(item)
        action: WriteAction = "reject" if item.status == "pending" else "delete"
        await self._writes.log(
            item=item, action=action, author=USER_AUTHOR, session_id=None, reason=None
        )
        await self._items.delete(item.id)
        await self.db.commit()  # before Qdrant: write lock released (orphans: re-indexing)
        await self.runtime.indexer.unindex(self.user_id, [item.id])
        for key in keys:
            await self.runtime.providers.storage.delete(self.user_id, key)

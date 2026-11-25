"""Document import (14.2): a file, a link or a pasted text becomes a queued `documents` row,
which the worker ingests. The received name is only a cleaned display name; the file is stored
under a generated key (`<user_id>/documents/<uuid4><canonical suffix>`). Neither messages nor
logs quote a file name, a link or a content."""

import builtins
import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from urllib.parse import urlsplit

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from app.db.models.memory import Document, DocumentSourceKind, MemoryItem
from app.features.memory.repository import DocumentRepository
from app.features.memory.schemas import DocumentError, DocumentOut
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.text import (
    clean_display,
    clean_text,
    display_name,
    source_hash,
)
from app.features.memory.service.upload import (
    MAX_PASTE_CHARS,
    MAX_UPLOAD_BYTES,
    SUFFIX_OF,
    classify_url,
    detect_upload,
    file_too_large,
    normalize_url,
)
from app.features.sessions.service import find_active_session
from app.providers.web.base import youtube_video_id

logger = logging.getLogger(__name__)

LIST_LIMIT = 200
READ_BLOCK = 1024 * 1024
STORAGE_CATEGORY = "documents"
LEARNED_GRAPH = "learned_document"


@dataclass(frozen=True)
class _Incoming:
    """Document to create, before its insertion. `data`: bytes to store (file or pasted
    text), `None` for a link."""

    kind: DocumentSourceKind
    name: str
    digest: str
    data: bytes | None = None
    suffix: str | None = None
    url: str | None = None
    tags: tuple[str, ...] = ()


def default_paste_title() -> str:
    return f"Pasted text from {date.today():%d/%m/%Y}"


def invalid_source() -> AppError:
    return AppError("invalid_document_source", "Provide one file, link, or text entry.", 422)


def to_document_out(doc: Document) -> DocumentOut:
    error = DocumentError.model_validate(doc.error) if doc.error else None
    return DocumentOut.model_validate(
        {
            "id": doc.id,
            "name": doc.name,
            "source_kind": doc.source_kind,
            "status": doc.status,
            "error": error,
            "url": doc.url,
            "size_bytes": doc.size_bytes,
            "item_id": doc.item_id,
            "learned": doc.learned,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }
    )


async def read_upload(file: UploadFile) -> bytes:
    """Chunked read; above `MAX_UPLOAD_BYTES`, 413 (exactly 20 MB goes through)."""
    blocks: list[bytes] = []
    size = 0
    while block := await file.read(READ_BLOCK):
        size += len(block)
        if size > MAX_UPLOAD_BYTES:
            raise file_too_large()
        blocks.append(block)
    return b"".join(blocks)


def _from_url(raw: str) -> _Incoming:
    url = normalize_url(raw)
    kind = classify_url(url)
    video = youtube_video_id(url)
    name = f"YouTube video {video}" if video else (urlsplit(url).hostname or "")
    return _Incoming(kind, display_name(name), source_hash(f"url:{url}".encode()), url=url)


def _from_text(text: str, title: str | None) -> _Incoming:
    if len(text) > MAX_PASTE_CHARS:
        raise AppError("paste_too_long", "Text can contain up to 500,000 characters.", 422)
    cleaned = clean_text(text)
    name = clean_display(title) or default_paste_title()
    data = cleaned.encode("utf-8")
    digest = source_hash(f"text:{cleaned}".encode())
    return _Incoming("paste", name, digest, data=data, suffix=SUFFIX_OF["text"])


class DocumentService:
    def __init__(self, db: AsyncSession, user_id: str, runtime: MemoryRuntime) -> None:
        self._db = db
        self._user_id = user_id
        self._runtime = runtime
        self._docs = DocumentRepository(db, user_id)

    async def create(
        self,
        *,
        file: UploadFile | None,
        url: str | None,
        text: str | None,
        title: str | None,
        tags: Sequence[str] = (),
    ) -> tuple[DocumentOut, bool]:
        """(document, new?). Exactly one source. Same content already imported: the existing
        one, unless it is in error or blocked, in which case it goes back in the queue
        (`_again`). The commit precedes queueing for the worker (which must see the row). `tags`:
        labels set by a feature (`cv`, `linkedin`, D124), added to those of an existing
        document."""
        url = url.strip() if url and url.strip() else None
        text = text if text and text.strip() else None
        if [file is not None, url is not None, text is not None].count(True) != 1:
            raise invalid_source()
        incoming = await self._incoming(file, url, text, title, tags)
        existing = await self._docs.find_by_source_hash(incoming.digest)
        if existing is not None:
            await self._tag(existing, incoming.tags)
            return await self._again(existing, incoming)
        doc, created = await self._insert(incoming)
        if not created:  # race lost: an identical import won
            return to_document_out(doc), False
        self._runtime.jobs.enqueue_ingest(self._user_id, doc.id)
        logger.info("Document %s en file (%s)", doc.id, doc.source_kind)
        return to_document_out(doc), True

    async def _incoming(
        self,
        file: UploadFile | None,
        url: str | None,
        text: str | None,
        title: str | None,
        tags: Sequence[str],
    ) -> _Incoming:
        if url is not None:
            incoming = _from_url(url)
        elif text is not None:
            incoming = _from_text(text, title)
        else:
            assert file is not None
            data = await read_upload(file)
            kind = detect_upload(file.filename, data)
            name = display_name(file.filename)
            incoming = _Incoming(kind, name, source_hash(data), data=data, suffix=SUFFIX_OF[kind])
        return replace(incoming, tags=tuple(tags))

    async def _tag(self, doc: Document, tags: tuple[str, ...]) -> None:
        """Labels added to an already imported document (validated at once)."""
        merged = list(dict.fromkeys([*map(str, doc.tags), *tags]))
        if merged != list(doc.tags):
            doc.tags = merged
            await self._db.commit()

    async def _again(self, existing: Document, incoming: _Incoming) -> tuple[DocumentOut, bool]:
        """Duplicate returned as is, unless it is in error, or queued or running with no job
        planned in this process (final status lost): it then goes back in the queue, error
        cleared, with the file just received (the old one is deleted after the commit)."""
        stuck = existing.status in ("queued", "processing")
        stuck = stuck and not self._runtime.jobs.is_scheduled(existing.id)
        if existing.status != "error" and not stuck:
            return to_document_out(existing), False
        old_key, new_key = existing.storage_key, await self._save(incoming)
        if new_key is not None:
            existing.storage_key, existing.size_bytes = new_key, len(incoming.data or b"")
        existing.status, existing.error = "queued", None
        await self._commit_files(new_key, old_key if new_key is not None else None)
        self._runtime.jobs.enqueue_ingest(self._user_id, existing.id)
        logger.info("Document %s remis en file", existing.id)
        return to_document_out(existing), True

    async def _save(self, incoming: _Incoming) -> str | None:
        if incoming.data is None or incoming.suffix is None:
            return None
        storage = self._runtime.providers.storage
        return await storage.save(self._user_id, STORAGE_CATEGORY, incoming.data, incoming.suffix)

    async def _commit_files(self, new_key: str | None, old_key: str | None) -> None:
        """Commit; if it fails, the new file is deleted, otherwise the old one."""
        storage = self._runtime.providers.storage
        try:
            await self._db.commit()
        except BaseException:
            if new_key is not None:
                await storage.delete(self._user_id, new_key)
            raise
        if old_key is not None:
            await storage.delete(self._user_id, old_key)

    async def _insert(self, incoming: _Incoming) -> tuple[Document, bool]:
        """File stored then row inserted and committed; any failure deletes the file. Race on
        the hash (uniqueness): the transaction is rolled back (it contains only this insertion,
        hence no SAVEPOINT, D65 c) and the winner is returned, `False`."""
        storage = self._runtime.providers.storage
        key = await self._save(incoming)
        committed = False
        try:
            doc = await self._docs.add(
                name=incoming.name,
                source_kind=incoming.kind,
                status="queued",
                url=incoming.url,
                storage_key=key,
                size_bytes=len(incoming.data) if incoming.data is not None else None,
                source_hash=incoming.digest,
                tags=list(incoming.tags),
            )
            await self._db.commit()
            committed = True
            return doc, True
        except IntegrityError:
            await self._db.rollback()
            winner = await self._docs.find_by_source_hash(incoming.digest)
            if winner is None:
                raise
            return winner, False
        finally:
            if key is not None and not committed:
                await storage.delete(self._user_id, key)

    async def mark_learned(self, document_id: str, runner: SessionRunner) -> str:
        """ "Already learned" (D68, D71): launches the `learned_document` flow on an indexed
        document and sets `learned`. Idempotent as long as a session of this document is open:
        it is returned instead of launching a second one (double click); a finished session no
        longer counts ("Relaunch"). The user lock only covers "session open? otherwise
        launch"; the request enters it with no pending write (otherwise the read's autoflush
        would hold SQLite's write lock while the runner writes the session with its own
        connection). The flag is written afterwards, outside the lock; a refused launch leaves
        it untouched."""
        doc = await self._docs.get(document_id)
        if doc is None:
            raise AppError("document_not_found", "Document not found.", 404)
        if doc.status != "indexed":
            raise AppError(
                "document_not_ready",
                "You can mark this document as already learned after indexing completes.",
                409,
            )
        async with self._runtime.learn_lock(self._user_id):
            session_id = await find_active_session(
                self._db,
                self._user_id,
                graph=LEARNED_GRAPH,
                subject_type="document",
                subject_id=doc.id,
            )
            if session_id is None:
                session_id = await runner.start(
                    self._user_id, LEARNED_GRAPH, {"document_id": doc.id}, "document", doc.id
                )
        doc.learned = True
        await self._db.flush()
        logger.info("Document %s marked already learned (session %s)", doc.id, session_id)
        return session_id

    async def list(self) -> list[DocumentOut]:
        return [to_document_out(doc) for doc in await self._docs.list_recent(LIST_LIMIT)]

    async def remove_for_item(self, item: MemoryItem) -> builtins.list[str]:
        """Deleting a `document` item (called by `MemoryService.delete`, which checked that the
        item is the user's): its `documents` rows are deleted and the keys of their files
        returned, to delete after the commit."""
        docs = {doc.id: doc for doc in await self._docs.for_item(item.id)}
        if item.source_id is not None and item.source_id not in docs:
            linked = await self._docs.get(item.source_id)
            if linked is not None:
                docs[linked.id] = linked
        for doc in docs.values():
            await self._docs.delete(doc.id)
        return [doc.storage_key for doc in docs.values() if doc.storage_key is not None]

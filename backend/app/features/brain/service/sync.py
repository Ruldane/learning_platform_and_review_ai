"""Authenticated relay channel. A write applies only to the declared revision."""

import re
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.brain import BrainFile, BrainFolder
from app.db.models.memory import Document
from app.features.brain.paths import path_excluded, relative_path
from app.features.brain.repository import FileRepository, FolderRepository, SyncTokenRepository
from app.features.brain.schemas import FileOut, InventoryOut, ReportIn, ReportOut, SyncTokenOut
from app.features.brain.service.folders import owned_folder
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.synced_files import (
    RemovedDocument,
    clean_removed_documents,
    delete_sync_file,
    prepare_sync_document,
    retire_sync_document,
    store_sync_document,
)

_PREFIX = "trsync_"
_TOKEN = re.compile(r"trsync_([a-zA-Z0-9_-]{1,36})\.[a-zA-Z0-9_-]{43}")


@dataclass(frozen=True)
class SyncIdentity:
    user_id: str
    digest: str


def _denied() -> AppError:
    return AppError("brain_sync_auth_required", "Sync token missing or invalid.", 401)


async def rotate_token(db: AsyncSession, user_id: str) -> SyncTokenOut:
    token = f"{_PREFIX}{user_id}.{token_urlsafe(32)}"
    await SyncTokenRepository(db, user_id).rotate(sha256(token.encode()).hexdigest())
    return SyncTokenOut(token=token)


async def read_identity(db: AsyncSession, token: str) -> SyncIdentity:
    match = _TOKEN.fullmatch(token) if len(token) <= 90 else None
    if match is None:
        raise _denied()
    identity = SyncIdentity(match.group(1), sha256(token.encode()).hexdigest())
    await _check_token(db, identity)
    return identity


async def _check_token(db: AsyncSession, identity: SyncIdentity) -> None:
    if not await SyncTokenRepository(db, identity.user_id).matches(identity.digest):
        raise _denied()


async def record_contact(db: AsyncSession, identity: SyncIdentity) -> None:
    await SyncTokenRepository(db, identity.user_id).record_contact(identity.digest)


async def _scope(
    db: AsyncSession,
    identity: SyncIdentity,
    folder_id: str,
    revision: int,
    *,
    write: bool,
) -> BrainFolder:
    if write:
        await FolderRepository(db, identity.user_id).begin_write()
        await _check_token(db, identity)
        await record_contact(db, identity)
    row = await owned_folder(db, identity.user_id, folder_id)
    if row.revision != revision:
        raise AppError("brain_revision_conflict", "The folder configuration has changed.", 409)
    if row.paused:
        raise AppError("brain_folder_paused", "Syncing for this folder is paused.", 409)
    return row


def _file_out(row: BrainFile, doc: Document) -> FileOut:
    return FileOut.model_validate(
        {
            "path": row.path,
            "sha256": row.sha256,
            "size": row.size,
            "document_id": doc.id,
            "status": doc.status,
        }
    )


async def inventory(
    db: AsyncSession,
    identity: SyncIdentity,
    folder_id: str,
    revision: int,
) -> InventoryOut:
    await _scope(db, identity, folder_id, revision, write=False)
    rows = await FileRepository(db, identity.user_id).inventory(folder_id)
    return InventoryOut(files=[_file_out(row, doc) for row, doc in rows])


@dataclass(frozen=True)
class SyncUpload:
    path: str
    digest: str
    data: bytes


async def ingest_file(
    db: AsyncSession,
    runtime: MemoryRuntime,
    identity: SyncIdentity,
    folder_id: str,
    revision: int,
    incoming: SyncUpload,
) -> FileOut:
    path = relative_path(incoming.path)
    data = incoming.data
    if sha256(data).hexdigest() != incoming.digest:
        raise AppError("brain_digest_mismatch", "The received digest does not match the file.", 422)
    draft = prepare_sync_document(path, data)
    folder = await _scope(db, identity, folder_id, revision, write=True)
    if path_excluded(path, folder.excluded_directories, folder.excluded_extensions):
        raise AppError("brain_path_excluded", "This note matches the folder's exclusions.", 422)
    user_id = identity.user_id
    repo = FileRepository(db, user_id)
    before = await repo.by_path(folder_id, path)
    if before is not None and before[0].sha256 == incoming.digest:
        row, doc = before
        await _enqueue(runtime, db, doc)
        return _file_out(row, doc)
    doc = await store_sync_document(db, runtime, user_id, draft)
    removed: RemovedDocument | None = None
    try:
        values = dict(document_id=doc.id, sha256=incoming.digest, size=len(data))
        if before is None:
            row = await repo.add(folder_id=folder_id, path=path, **values)
        else:
            row, previous = before
            row.document_id, row.sha256, row.size = doc.id, incoming.digest, len(data)
            await db.flush()
            removed = await retire_sync_document(db, user_id, previous.id)
        await db.commit()
    except BaseException:
        if doc.storage_key is not None:
            await delete_sync_file(runtime, user_id, doc.storage_key)
        raise
    runtime.jobs.enqueue_ingest(user_id, doc.id)
    if removed is not None:
        await clean_removed_documents(runtime, user_id, [removed])
    return _file_out(row, doc)


async def _enqueue(runtime: MemoryRuntime, db: AsyncSession, doc: Document) -> None:
    retry = doc.status in ("error", "queued", "processing") and not runtime.jobs.is_scheduled(
        doc.id
    )
    if retry:
        doc.status, doc.error = "queued", None
    await db.commit()
    if retry:
        runtime.jobs.enqueue_ingest(doc.user_id, doc.id)


async def remove_file(
    db: AsyncSession,
    runtime: MemoryRuntime,
    identity: SyncIdentity,
    folder_id: str,
    revision: int,
    path: str,
) -> None:
    path = relative_path(path)
    await _scope(db, identity, folder_id, revision, write=True)
    user_id = identity.user_id
    before = await FileRepository(db, user_id).by_path(folder_id, path)
    removed = await retire_sync_document(db, user_id, before[1].id) if before is not None else None
    await db.commit()
    if removed is not None:
        await clean_removed_documents(runtime, user_id, [removed])


async def store_report(
    db: AsyncSession,
    identity: SyncIdentity,
    folder_id: str,
    revision: int,
    body: ReportIn,
) -> None:
    row = await _scope(db, identity, folder_id, revision, write=True)
    report = ReportOut.model_validate({**body.model_dump(by_alias=True), "reported_at": utcnow()})
    row.report = report.model_dump(mode="json", by_alias=True)

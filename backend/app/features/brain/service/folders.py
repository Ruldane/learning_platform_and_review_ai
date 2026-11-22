"""Gestion des racines déclarées par le compte et bilan public sans les chemins."""

from collections import Counter

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.brain import BrainFolder
from app.features.brain.paths import root_path
from app.features.brain.repository import FileRepository, FolderRepository
from app.features.brain.schemas import FolderIn, FolderOut, FolderPatch, FolderStatus
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.synced_files import (
    RemovedDocument,
    clean_removed_documents,
    retire_sync_document,
)


async def folders(db: AsyncSession, user_id: str) -> list[FolderOut]:
    return [FolderOut.model_validate(row) for row in await FolderRepository(db, user_id).ordered()]


async def owned_folder(db: AsyncSession, user_id: str, folder_id: str) -> BrainFolder:
    row = await FolderRepository(db, user_id).get(folder_id)
    if row is None:
        raise AppError("brain_folder_not_found", "Dossier introuvable.", 404)
    return row


def _exists() -> AppError:
    return AppError("brain_folder_exists", "Ce dossier est déjà enregistré.", 409)


async def create_folder(db: AsyncSession, user_id: str, body: FolderIn) -> FolderOut:
    path = root_path(body.path)
    try:
        row = await FolderRepository(db, user_id).add(name=body.name, path=path, paused=body.paused)
    except IntegrityError:
        raise _exists() from None
    return FolderOut.model_validate(row)


async def _retire_folder(db: AsyncSession, user_id: str, folder_id: str) -> list[RemovedDocument]:
    removed = []
    for _, doc in await FileRepository(db, user_id).inventory(folder_id):
        if result := await retire_sync_document(db, user_id, doc.id):
            removed.append(result)
    return removed


async def patch_folder(
    db: AsyncSession,
    runtime: MemoryRuntime,
    user_id: str,
    folder_id: str,
    body: FolderPatch,
) -> FolderOut:
    await FolderRepository(db, user_id).begin_write()
    row = await owned_folder(db, user_id, folder_id)
    path = root_path(body.path) if body.path is not None else row.path
    name = body.name if body.name is not None else row.name
    paused = body.paused if body.paused is not None else row.paused
    if (path, name, paused) == (row.path, row.name, row.paused):
        return FolderOut.model_validate(row)
    removed = await _retire_folder(db, user_id, folder_id) if path != row.path else []
    row.path, row.name, row.paused, row.report = path, name, paused, None
    row.revision += 1
    try:
        await db.commit()
    except IntegrityError:
        raise _exists() from None
    await clean_removed_documents(runtime, user_id, removed)
    return FolderOut.model_validate(row)


async def remove_folder(
    db: AsyncSession,
    runtime: MemoryRuntime,
    user_id: str,
    folder_id: str,
) -> None:
    repo = FolderRepository(db, user_id)
    await repo.begin_write()
    await owned_folder(db, user_id, folder_id)
    removed = await _retire_folder(db, user_id, folder_id)
    await repo.delete(folder_id)
    await db.commit()
    await clean_removed_documents(runtime, user_id, removed)


async def status(db: AsyncSession, user_id: str) -> list[FolderStatus]:
    rows = await FolderRepository(db, user_id).ordered()
    counts = await FileRepository(db, user_id).counts()
    return [_status(row, counts.get(row.id, Counter())) for row in rows]


def _status(row: BrainFolder, count: Counter[str]) -> FolderStatus:
    return FolderStatus.model_validate(
        {
            "id": row.id,
            "name": row.name,
            "paused": row.paused,
            "revision": row.revision,
            "total": sum(count.values()),
            "queued": count["queued"],
            "processing": count["processing"],
            "indexed": count["indexed"],
            "error": count["error"],
            "report": row.report,
        }
    )

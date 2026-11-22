"""Dossiers Cerveau et canal réservé au synchroniseur local."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, Request, Response, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.caller import MCP_IDENTITY
from app.core.deps import CurrentUserDep, Db, InterfaceUserDep
from app.features.brain.router_chat import router as chat_router
from app.features.brain.schemas import (
    Digest,
    FileOut,
    FolderIn,
    FolderOut,
    FolderPatch,
    FolderStatus,
    InventoryOut,
    RelativePath,
    RemoveIn,
    ReportIn,
    SyncTokenOut,
)
from app.features.brain.service import folders, sync
from app.features.memory.service.documents import read_upload
from app.features.memory.service.runtime import MemoryRuntime

router = APIRouter(prefix="/brain", tags=["brain"])
router.include_router(chat_router)

_bearer = HTTPBearer(auto_error=False, scheme_name="BrainSyncBearer")
Revision = Annotated[int, Header(ge=1, alias="X-Tremplin-Folder-Revision")]


def _memory(request: Request) -> MemoryRuntime:
    runtime: MemoryRuntime = request.app.state.memory
    return runtime


async def _identity(
    db: Db,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> sync.SyncIdentity:
    token = (
        credentials.credentials if credentials is not None and MCP_IDENTITY.get() is None else ""
    )
    return await sync.read_identity(db, token)


SyncUser = Annotated[sync.SyncIdentity, Depends(_identity)]
MemoryDep = Annotated[MemoryRuntime, Depends(_memory)]


@router.get("/status", response_model=list[FolderStatus])
async def status_view(db: Db, current: CurrentUserDep) -> list[FolderStatus]:
    """État de synchronisation des dossiers, sans chemins locaux ni fichiers individuels."""
    return await folders.status(db, current.id)


@router.get("/folders", response_model=list[FolderOut])
async def list_folders(db: Db, current: InterfaceUserDep) -> list[FolderOut]:
    return await folders.folders(db, current.id)


@router.post("/folders", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def add_folder(db: Db, current: InterfaceUserDep, body: FolderIn) -> FolderOut:
    return await folders.create_folder(db, current.id, body)


@router.patch("/folders/{folder_id}", response_model=FolderOut)
async def patch_folder(
    db: Db,
    current: InterfaceUserDep,
    runtime: MemoryDep,
    folder_id: str,
    body: FolderPatch,
) -> FolderOut:
    return await folders.patch_folder(db, runtime, current.id, folder_id, body)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    db: Db, current: InterfaceUserDep, runtime: MemoryDep, folder_id: str
) -> None:
    await folders.remove_folder(db, runtime, current.id, folder_id)


@router.post("/sync-token", response_model=SyncTokenOut, status_code=status.HTTP_201_CREATED)
async def create_sync_token(db: Db, current: InterfaceUserDep, response: Response) -> SyncTokenOut:
    """Crée le jeton du relais et invalide le précédent. La valeur n'est rendue qu'une fois."""
    response.headers["Cache-Control"] = "no-store"
    return await sync.rotate_token(db, current.id)


@router.get("/sync/folders", response_model=list[FolderOut])
async def sync_folders(db: Db, identity: SyncUser) -> list[FolderOut]:
    return await folders.folders(db, identity.user_id)


@router.get("/sync/folders/{folder_id}/inventory", response_model=InventoryOut)
async def sync_inventory(
    db: Db, identity: SyncUser, folder_id: str, revision: Revision
) -> InventoryOut:
    return await sync.inventory(db, identity, folder_id, revision)


@router.post(
    "/sync/folders/{folder_id}/files", response_model=FileOut, status_code=status.HTTP_202_ACCEPTED
)
async def sync_file(
    db: Db,
    identity: SyncUser,
    runtime: MemoryDep,
    folder_id: str,
    revision: Revision,
    path: Annotated[RelativePath, Form()],
    sha256: Annotated[Digest, Form()],
    file: Annotated[UploadFile, File()],
) -> FileOut:
    incoming = sync.SyncUpload(path, sha256, await read_upload(file))
    return await sync.ingest_file(db, runtime, identity, folder_id, revision, incoming)


@router.post("/sync/folders/{folder_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
async def sync_remove(
    db: Db,
    identity: SyncUser,
    runtime: MemoryDep,
    folder_id: str,
    revision: Revision,
    body: RemoveIn,
) -> None:
    await sync.remove_file(db, runtime, identity, folder_id, revision, body.path)


@router.post("/sync/folders/{folder_id}/report", status_code=status.HTTP_204_NO_CONTENT)
async def sync_report(
    db: Db,
    identity: SyncUser,
    folder_id: str,
    revision: Revision,
    body: ReportIn,
) -> None:
    await sync.store_report(db, identity, folder_id, revision, body)

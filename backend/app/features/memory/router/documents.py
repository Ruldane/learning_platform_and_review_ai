"""Document import (14.2): `POST /documents` (multipart: one file or one link, only one),
`POST /documents/text` (JSON: pasted text and title) and `GET /documents`. Pasted text goes
as JSON: a non-file multipart field is capped at 1 MiB by Starlette, which would answer a
generic 400. The body size is bounded before parsing by `app.core.limits.BodySizeLimit`;
the file is bounded again when read."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi import status as http

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.memory.router.deps import MemoryRuntimeDep
from app.features.memory.schemas import DocumentCreated, DocumentOut, LearnedStarted, PasteCreate
from app.features.memory.service.documents import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": DocumentCreated, "description": "Content already imported"}
}


def _service(current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep) -> DocumentService:
    return DocumentService(db, current.id, runtime)


Service = Annotated[DocumentService, Depends(_service)]


def _created(response: Response, document: DocumentOut, new: bool) -> DocumentCreated:
    """202: new document or document requeued; 200: duplicate (existing)."""
    if not new:
        response.status_code = http.HTTP_200_OK
    return DocumentCreated(document=document, duplicate=not new)


@router.post(
    "", status_code=http.HTTP_202_ACCEPTED, response_model=DocumentCreated, responses=_RESPONSES
)
async def create_document(
    response: Response,
    service: Service,
    file: Annotated[UploadFile | None, File()] = None,
    url: Annotated[str | None, Form(max_length=2048)] = None,
) -> DocumentCreated:
    document, new = await service.create(file=file, url=url, text=None, title=None)
    return _created(response, document, new)


@router.post(
    "/text",
    status_code=http.HTTP_202_ACCEPTED,
    response_model=DocumentCreated,
    responses=_RESPONSES,
)
async def paste_document(
    response: Response, service: Service, body: PasteCreate
) -> DocumentCreated:
    document, new = await service.create(file=None, url=None, text=body.text, title=body.title)
    return _created(response, document, new)


@router.post(
    "/{document_id}/learned", status_code=http.HTTP_202_ACCEPTED, response_model=LearnedStarted
)
async def mark_learned(document_id: str, service: Service, runtime: RuntimeDep) -> LearnedStarted:
    """ "Already learned": the Archivist creates declared skills from the indexed document."""
    return LearnedStarted(session_id=await service.mark_learned(document_id, runtime.runner))


@router.get("", response_model=list[DocumentOut])
async def list_documents(service: Service) -> list[DocumentOut]:
    """The 200 most recent, newest first."""
    return await service.list()

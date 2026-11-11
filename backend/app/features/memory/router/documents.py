"""Import des documents (14.2) : `POST /documents` (multipart : un fichier, un lien ou un texte
collé, un seul) et `GET /documents`. La taille du corps est bornée avant l'analyse du multipart
par `app.core.limits.BodySizeLimit` ; le fichier l'est encore à sa lecture."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi import status as http

from app.core.deps import CurrentUserDep, Db
from app.features.memory.router.deps import MemoryRuntimeDep
from app.features.memory.schemas import DocumentCreated, DocumentOut
from app.features.memory.service.documents import DocumentService
from app.features.memory.service.upload import MAX_PASTE_CHARS

router = APIRouter(prefix="/documents", tags=["documents"])


def _service(current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep) -> DocumentService:
    return DocumentService(db, current.id, runtime)


Service = Annotated[DocumentService, Depends(_service)]


@router.post(
    "",
    status_code=http.HTTP_202_ACCEPTED,
    response_model=DocumentCreated,
    responses={200: {"model": DocumentCreated, "description": "Contenu déjà importé"}},
)
async def create_document(
    response: Response,
    service: Service,
    file: Annotated[UploadFile | None, File()] = None,
    url: Annotated[str | None, Form(max_length=2048)] = None,
    text: Annotated[str | None, Form(max_length=MAX_PASTE_CHARS)] = None,
    title: Annotated[str | None, Form(max_length=200)] = None,
) -> DocumentCreated:
    """202 : nouveau document ou document en erreur remis en file ; 200 : doublon (existant)."""
    document, new = await service.create(file=file, url=url, text=text, title=title)
    if not new:
        response.status_code = http.HTTP_200_OK
    return DocumentCreated(document=document, duplicate=not new)


@router.get("", response_model=list[DocumentOut])
async def list_documents(service: Service) -> list[DocumentOut]:
    """Les 200 plus récents, du plus récent au plus ancien."""
    return await service.list()

"""Import des documents (14.2) : `POST /documents` (multipart : un fichier ou un lien, un seul),
`POST /documents/text` (JSON : texte collé et titre) et `GET /documents`. Le texte collé passe
en JSON : un champ multipart autre qu'un fichier est plafonné à 1 Mio par Starlette, qui
répondrait une 400 générique. La taille du corps est bornée avant l'analyse par
`app.core.limits.BodySizeLimit` ; le fichier l'est encore à sa lecture."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi import status as http

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.memory.router.deps import MemoryRuntimeDep
from app.features.memory.schemas import DocumentCreated, DocumentOut, LearnedStarted, PasteCreate
from app.features.memory.service.documents import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": DocumentCreated, "description": "Contenu déjà importé"}
}


def _service(current: CurrentUserDep, db: Db, runtime: MemoryRuntimeDep) -> DocumentService:
    return DocumentService(db, current.id, runtime)


Service = Annotated[DocumentService, Depends(_service)]


def _created(response: Response, document: DocumentOut, new: bool) -> DocumentCreated:
    """202 : nouveau document ou document remis en file ; 200 : doublon (existant)."""
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
    """« Déjà appris » : l'Archiviste crée des acquis déclarés à partir du document indexé."""
    return LearnedStarted(session_id=await service.mark_learned(document_id, runtime.runner))


@router.get("", response_model=list[DocumentOut])
async def list_documents(service: Service) -> list[DocumentOut]:
    """Les 200 plus récents, du plus récent au plus ancien."""
    return await service.list()

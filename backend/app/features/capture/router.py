"""API de la capture rapide et du journal (SPEC F18, D108). `POST /capture` lance l'Archiviste sur
un lien, un texte ou un document importé ; ses questions (texte d'un lien illisible, tâche à
cocher, fiches) passent par la reprise de la session (`POST /sessions/{id}/resume`, 14.1).
`GET /journal` rend le journal, le plus récent d'abord."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.capture.schemas import (
    CaptureRequest,
    CaptureStarted,
    JournalKind,
    JournalPage,
)
from app.features.capture.service import capture
from app.features.capture.service.journal import journal_page
from app.features.capture.service.runtime import CaptureRuntime

router = APIRouter(tags=["capture"])


def get_capture_runtime(conn: HTTPConnection) -> CaptureRuntime:
    """La capture ouverte par le lifespan (`app.state.capture`)."""
    runtime: CaptureRuntime = conn.app.state.capture
    return runtime


CaptureDep = Annotated[CaptureRuntime, Depends(get_capture_runtime)]


@router.post("/capture", response_model=CaptureStarted, status_code=status.HTTP_202_ACCEPTED)
async def start_capture(
    body: CaptureRequest, current: CurrentUserDep, rt: CaptureDep
) -> CaptureStarted:
    """Lance la capture. Zéro ou plusieurs sources : 422 `invalid_input` ; lien non http(s) :
    422 `invalid_url` ; document d'une autre : 404 `document_not_found`."""
    return await capture.start_capture(rt, current.id, body)


@router.get("/journal", response_model=JournalPage)
async def read_journal(
    current: CurrentUserDep,
    db: Db,
    kind: JournalKind | None = None,
    before: Annotated[str | None, Query(max_length=36)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JournalPage:
    """Le journal (captures, sessions, quiz, bilans hebdomadaires), le plus récent d'abord ;
    `before` : `next_before` de la page précédente."""
    return await journal_page(db, current.id, kind=kind, before=before, limit=limit)

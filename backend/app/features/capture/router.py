"""Quick capture and journal API (SPEC F18, D108). `POST /capture` launches the Archivist on a
link, a text or an imported document; its questions (text of an unreadable link, task to tick,
cards) go through the session's resume (`POST /sessions/{id}/resume`, 14.1). `GET /journal`
returns the journal, most recent first."""

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
    """The capture opened by the lifespan (`app.state.capture`)."""
    runtime: CaptureRuntime = conn.app.state.capture
    return runtime


CaptureDep = Annotated[CaptureRuntime, Depends(get_capture_runtime)]


@router.post("/capture", response_model=CaptureStarted, status_code=status.HTTP_202_ACCEPTED)
async def start_capture(
    body: CaptureRequest, current: CurrentUserDep, rt: CaptureDep
) -> CaptureStarted:
    """Launches the capture. Zero or several sources: 422 `invalid_input`; non-http(s) link:
    422 `invalid_url`; another user's document: 404 `document_not_found`."""
    return await capture.start_capture(rt, current.id, body)


@router.get("/journal", response_model=JournalPage)
async def read_journal(
    current: CurrentUserDep,
    db: Db,
    kind: JournalKind | None = None,
    before: Annotated[str | None, Query(max_length=36)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JournalPage:
    """The journal (captures, sessions, quizzes, weekly reviews), most recent first;
    `before`: `next_before` of the previous page."""
    return await journal_page(db, current.id, kind=kind, before=before, limit=limit)

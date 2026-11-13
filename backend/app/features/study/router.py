"""API de la session guidée (SPEC F14, 14.2 ; D103). `POST /study-sessions` et `PATCH
/study-sessions/{id}` sont ceux de 14.2 ; hors 14.2 : `GET /study-sessions/summary` (série et
heures visibles en permanence, bloc du jour) et `GET /study-sessions/{id}` (écran de fin). Le
résumé est déclaré avant `/{id}`. Tout est filtré par utilisatrice : la session d'une autre
donne 404."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.study.schemas import (
    StudySessionOut,
    StudyStart,
    StudyStarted,
    StudySummaryOut,
    StudyUpdate,
)
from app.features.study.service import control, sessions, view
from app.features.study.service.runtime import StudyRuntime

router = APIRouter(tags=["study"])


def get_study_runtime(conn: HTTPConnection) -> StudyRuntime:
    """L'étude ouverte par le lifespan (`app.state.study`)."""
    runtime: StudyRuntime = conn.app.state.study
    return runtime


StudyDep = Annotated[StudyRuntime, Depends(get_study_runtime)]
_ALREADY: dict[int | str, dict[str, Any]] = {
    200: {"model": StudyStarted, "description": "Session déjà ouverte sur cette leçon."}
}


@router.post(
    "/study-sessions",
    response_model=StudyStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_ALREADY,
)
async def start_study(
    body: StudyStart, current: CurrentUserDep, rt: StudyDep, response: Response
) -> StudyStarted:
    """Ouvre une session et lance le Tuteur (202). `lesson_id` absent : bloc du jour (404
    `no_block_today`) ; leçon pas prête : 409 `lesson_not_ready` ; session déjà ouverte sur la
    même leçon : 200, elle-même ; sur une autre : 409 `study_already_open`."""
    started, created = await sessions.start_study(rt, current.id, body)
    if not created:
        response.status_code = status.HTTP_200_OK
    return started


@router.get("/study-sessions/summary", response_model=StudySummaryOut)
async def study_summary(current: CurrentUserDep, db: Db, rt: StudyDep) -> StudySummaryOut:
    """Série (jours locaux avec une session terminée), minutes de la semaine, minuteur, session
    ouverte et bloc du jour."""
    return await view.summary(rt, db, current.id)


@router.get("/study-sessions/{study_session_id}", response_model=StudySessionOut)
async def get_study(study_session_id: str, current: CurrentUserDep, db: Db) -> StudySessionOut:
    return await view.session_out(db, current.id, study_session_id)


@router.patch(
    "/study-sessions/{study_session_id}",
    response_model=StudySessionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def update_study(
    study_session_id: str,
    body: StudyUpdate,
    current: CurrentUserDep,
    runtime: RuntimeDep,
    rt: StudyDep,
) -> StudySessionOut:
    """« Terminer » (`finish`, minuteur gardé puis question en attente reprise ; Tuteur en
    train d'écrire : 409 `study_not_waiting`) ou « Abandonner » (`cancel`, rien n'est écrit).
    Déjà terminée ou abandonnée : l'état, sans rien changer."""
    return await control.update_study(runtime, rt, current.id, study_session_id, body)

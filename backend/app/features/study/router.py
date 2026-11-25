"""Guided session API (SPEC F14, 14.2; D103). `POST /study-sessions` and `PATCH
/study-sessions/{id}` are those of 14.2; outside 14.2: `GET /study-sessions/summary` (streak
and hours always visible, today's block) and `GET /study-sessions/{id}` (end screen). The
summary is declared before `/{id}`. Everything is filtered by user: another user's session
gives 404."""

from typing import Any

from fastapi import APIRouter, Response, status

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db, RuntimeDep
from app.features.study.router_deps import StudyDep
from app.features.study.router_training import router as training_router
from app.features.study.schemas import (
    StudySessionOut,
    StudyStart,
    StudyStarted,
    StudySummaryOut,
    StudyUpdate,
)
from app.features.study.service import control, sessions, view

router = APIRouter(tags=["study"])
router.include_router(training_router)

_ALREADY: dict[int | str, dict[str, Any]] = {
    200: {"model": StudyStarted, "description": "Session already open on this lesson."}
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
    """Opens a session and launches the Tutor (202). `lesson_id` absent: today's block (404
    `no_block_today`); lesson not ready: 409 `lesson_not_ready`; session already open on the
    same lesson: 200, itself; on another one: 409 `study_already_open`."""
    started, created = await sessions.start_study(rt, current.id, body)
    if not created:
        response.status_code = status.HTTP_200_OK
    return started


@router.get("/study-sessions/summary", response_model=StudySummaryOut)
async def study_summary(current: CurrentUserDep, db: Db, rt: StudyDep) -> StudySummaryOut:
    """Streak (local days with a finished session), minutes of the week, timer, open session
    and today's block."""
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
    current: ConfirmedUserDep,
    runtime: RuntimeDep,
    rt: StudyDep,
) -> StudySessionOut:
    """ "Finish" (`finish`, timer kept then waiting question resumed; Tutor writing: 409
    `study_not_waiting`) or "Abandon" (`cancel`, nothing is written). Already finished or
    abandoned: the state, without changing anything."""
    return await control.update_study(runtime, rt, current.id, study_session_id, body)

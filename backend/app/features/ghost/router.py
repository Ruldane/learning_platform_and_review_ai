from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, Db
from app.core.practice import PracticeSummary
from app.features.ide.service.ghost import read_history as read_ide_history
from app.features.quiz.service.ghost import read_history as read_quiz_history

router = APIRouter(tags=["ghost"])


@router.get("/quizzes/{quiz_id}/ghost")
async def quiz_ghost(
    quiz_id: str,
    current: CurrentUserDep,
    db: Db,
    attempt_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[PracticeSummary]:
    """Recent markers and the attempt optionally chosen from the log, without answers."""
    return await read_quiz_history(db, current.id, quiz_id, attempt_id)


@router.get("/ide/sessions/{session_id}/ghost")
async def ide_ghost(
    session_id: str,
    current: CurrentUserDep,
    db: Db,
    run_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[PracticeSummary]:
    """Markers of personal checks, including the log reference, without output."""
    return await read_ide_history(db, current.id, session_id, run_id)

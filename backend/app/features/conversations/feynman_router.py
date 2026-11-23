from uuid import UUID

from fastapi import APIRouter

from app.agents.tools.feynman_port import FEYNMAN_IDE, FEYNMAN_LESSON
from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db, RuntimeDep
from app.core.field_paths import FieldPathsRoute
from app.features.conversations import feynman
from app.features.conversations.feynman_schemas import (
    FeynmanFileStart,
    FeynmanRunOut,
    FeynmanSaved,
    FeynmanStart,
)
from app.features.conversations.schemas import ConversationStarted

router = APIRouter(tags=["conversations"], route_class=FieldPathsRoute)


@router.get("/lessons/{lesson_id}/explain")
async def latest_lesson_explanation(
    lesson_id: UUID, db: Db, user: CurrentUserDep
) -> FeynmanRunOut | None:
    return await feynman.latest(db, user.id, str(lesson_id), FEYNMAN_LESSON)


@router.post("/lessons/{lesson_id}/explain", status_code=202)
async def explain_lesson(
    lesson_id: UUID, body: FeynmanStart, db: Db, user: CurrentUserDep, runtime: RuntimeDep
) -> ConversationStarted:
    return await feynman.start(runtime.runner, db, user.id, str(lesson_id), body)


@router.get("/ide/sessions/{session_id}/explain")
async def latest_ide_explanation(
    session_id: UUID, db: Db, user: CurrentUserDep
) -> FeynmanRunOut | None:
    return await feynman.latest(db, user.id, str(session_id), FEYNMAN_IDE)


@router.post("/ide/sessions/{session_id}/explain", status_code=202)
async def explain_file(
    session_id: UUID, body: FeynmanFileStart, db: Db, user: CurrentUserDep, runtime: RuntimeDep
) -> ConversationStarted:
    return await feynman.start(runtime.runner, db, user.id, str(session_id), body)


@router.get("/conversations/explain/{turn_id}")
async def read_explanation(turn_id: UUID, db: Db, user: CurrentUserDep) -> FeynmanRunOut:
    return await feynman.read(db, user.id, str(turn_id))


@router.post("/conversations/explain/{turn_id}/accept")
async def accept_explanation(turn_id: UUID, db: Db, user: ConfirmedUserDep) -> FeynmanSaved:
    return await feynman.accept(db, user.id, str(turn_id))

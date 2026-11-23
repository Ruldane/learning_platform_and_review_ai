from uuid import UUID

from fastapi import APIRouter, Response

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db, RuntimeDep
from app.features.conversations.service import ConversationQuestionIn, ConversationStarted
from app.features.study.router_deps import StudyDep
from app.features.study.service.training import (
    open_training,
    start_training,
    talk_to_tutor,
    training_out,
    training_row,
)
from app.features.study.service.training_end import update_training
from app.features.study.training_schemas import (
    TrainingContextUpdate,
    TrainingSessionOut,
    TrainingStart,
    TrainingUpdate,
)

router = APIRouter(prefix="/study-sessions/training", tags=["study"])


@router.post("", status_code=202, responses={200: {"model": TrainingSessionOut}})
async def start(
    body: TrainingStart, user: CurrentUserDep, rt: StudyDep, response: Response
) -> TrainingSessionOut:
    output, created = await start_training(rt, user.id, body)
    if not created:
        response.status_code = 200
    return output


@router.get("/open")
async def opened(user: CurrentUserDep, db: Db) -> TrainingSessionOut | None:
    return await open_training(db, user.id)


@router.get("/{study_session_id}")
async def read(study_session_id: UUID, user: CurrentUserDep, db: Db) -> TrainingSessionOut:
    return await training_out(db, await training_row(db, user.id, str(study_session_id)))


@router.post("/{study_session_id}/messages", status_code=202)
async def message(
    study_session_id: UUID,
    body: ConversationQuestionIn,
    user: CurrentUserDep,
    db: Db,
    runtime: RuntimeDep,
) -> ConversationStarted:
    return await talk_to_tutor(runtime.runner, db, user.id, str(study_session_id), body)


@router.patch("/{study_session_id}")
async def update(
    study_session_id: UUID,
    body: TrainingUpdate,
    user: ConfirmedUserDep,
    rt: StudyDep,
    runtime: RuntimeDep,
) -> TrainingSessionOut:
    return await update_training(runtime.runner, rt, user.id, str(study_session_id), body)


@router.patch("/{study_session_id}/context")
async def update_context(
    study_session_id: UUID,
    body: TrainingContextUpdate,
    user: CurrentUserDep,
    rt: StudyDep,
    runtime: RuntimeDep,
) -> TrainingSessionOut:
    return await update_training(runtime.runner, rt, user.id, str(study_session_id), body)

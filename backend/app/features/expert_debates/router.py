from uuid import UUID

from fastapi import APIRouter

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db, RuntimeDep
from app.features.conversations.service import ConversationQuestionIn
from app.features.expert_debates.schemas import (
    ExpertDebateOut,
    ExpertDebateStarted,
    ExpertDebateSummary,
    ExpertJudgmentIn,
)
from app.features.expert_debates.service import ExpertDebates, start_debate

router = APIRouter(prefix="/expert-debates", tags=["expert-debates"])


@router.get("")
async def list_debates(db: Db, user: CurrentUserDep) -> list[ExpertDebateSummary]:
    return await ExpertDebates(db, user.id).list()


@router.post("", status_code=202)
async def open_debate(
    body: ConversationQuestionIn, db: Db, user: CurrentUserDep, runtime: RuntimeDep
) -> ExpertDebateStarted:
    return await start_debate(runtime.runner, db, user.id, body)


@router.get("/{debate_id}")
async def get_debate(debate_id: UUID, db: Db, user: CurrentUserDep) -> ExpertDebateOut:
    return await ExpertDebates(db, user.id).read(debate_id)


@router.put("/{debate_id}/judgment")
async def put_judgment(
    debate_id: UUID, body: ExpertJudgmentIn, db: Db, user: ConfirmedUserDep
) -> ExpertDebateOut:
    return await ExpertDebates(db, user.id).judge(debate_id, body.text)

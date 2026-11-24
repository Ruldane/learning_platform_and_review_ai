"""Learning API (SPEC 14.2, D87): goals (creating one starts the Council, a retry restarts it
after a failure, D97), proposals of the latest batch, path choice, board states. The Council's
other actions (framing answer, commands, messages) go through the session routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import status as http
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.learning.schemas import (
    BoardEdit,
    BoardOut,
    ChooseOut,
    ChooseRequest,
    GoalCreate,
    GoalOut,
    GoalStarted,
    ProposalOut,
)
from app.features.learning.service import boards, choice, goals, launching, proposals
from app.features.learning.service.runtime import LearningRuntime

router = APIRouter(tags=["learning"])


def get_learning_runtime(conn: HTTPConnection) -> LearningRuntime:
    """The learning runtime opened by the lifespan (`app.state.learning`)."""
    runtime: LearningRuntime = conn.app.state.learning
    return runtime


LearningDep = Annotated[LearningRuntime, Depends(get_learning_runtime)]


@router.post("/goals", status_code=http.HTTP_201_CREATED, response_model=GoalStarted)
async def create_goal(
    body: GoalCreate, current: CurrentUserDep, db: Db, learning: LearningDep
) -> GoalStarted:
    return await goals.create_goal(db, learning, current.id, body)


@router.post("/goals/direct", status_code=http.HTTP_201_CREATED, response_model=GoalOut)
async def write_goal(body: GoalCreate, current: CurrentUserDep, db: Db) -> GoalOut:
    """Writes a goal without starting the Council (no agent, no model call): same fields as
    `POST /goals`."""
    return await goals.write_goal(db, current.id, body)


@router.get("/goals", response_model=list[GoalOut])
async def list_goals(current: CurrentUserDep, db: Db) -> list[GoalOut]:
    return await goals.list_goals(db, current.id)


@router.get("/goals/{goal_id}", response_model=GoalOut)
async def get_goal(goal_id: str, current: CurrentUserDep, db: Db) -> GoalOut:
    return await goals.get_goal(db, current.id, goal_id)


@router.post(
    "/goals/{goal_id}/council", status_code=http.HTTP_202_ACCEPTED, response_model=GoalStarted
)
async def retry_council(
    goal_id: str, current: CurrentUserDep, learning: LearningDep
) -> GoalStarted:
    """Restarts the goal's Council from the beginning, only if its latest session failed
    (409 `council_not_failed` otherwise, `goal_already_chosen` if a program was started)."""
    return await launching.retry_council(learning, current.id, goal_id)


@router.get("/goals/{goal_id}/proposals", response_model=list[ProposalOut])
async def list_proposals(goal_id: str, current: CurrentUserDep, db: Db) -> list[ProposalOut]:
    return await proposals.list_latest(db, current.id, goal_id)


@router.post(
    "/proposals/{proposal_id}/choose", status_code=http.HTTP_202_ACCEPTED, response_model=ChooseOut
)
async def choose_proposal(
    proposal_id: str,
    body: ChooseRequest,
    current: CurrentUserDep,
    db: Db,
    runtime: RuntimeDep,
    learning: LearningDep,
) -> ChooseOut:
    return await choice.choose(runtime, learning, db, current.id, proposal_id, body)


@router.get("/goals/{goal_id}/boards", response_model=list[BoardOut])
async def list_boards(goal_id: str, current: CurrentUserDep, db: Db) -> list[BoardOut]:
    return await boards.list_boards(db, current.id, goal_id)


@router.post("/boards/{board_id}/edits", status_code=http.HTTP_201_CREATED, response_model=BoardOut)
async def edit_board(
    board_id: str, body: BoardEdit, current: CurrentUserDep, db: Db, runtime: RuntimeDep
) -> BoardOut:
    return await boards.save_edit(db, runtime, current.id, board_id, body)

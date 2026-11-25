"""Skills map API (SPEC F15, 14.2; D107). The fixed routes (`graph`, `compare`, `history`) are
declared before `/skills/{skill_id}`. Everything is filtered by user: another user's skill or goal
gives 404. Reads without cache (`Cache-Control: no-store`): a level change shows on the front
end's next re-read (every 30 s)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.deps import CurrentUserDep, Db
from app.features.skills.compare import compare_with
from app.features.skills.history import DEFAULT_WEEKS, MAX_WEEKS, skill_history
from app.features.skills.map import skill_detail, skill_graph
from app.features.skills.schemas import (
    CompareOut,
    CompareTarget,
    HistoryOut,
    SkillCreate,
    SkillCreated,
    SkillDetailOut,
    SkillGraphOut,
)
from app.features.skills.service import SkillsService

router = APIRouter(prefix="/skills", tags=["skills"])


def clock() -> datetime:
    """Now (UTC); replaced by the tests (`app.dependency_overrides`)."""
    return datetime.now(UTC)


NowDep = Annotated[datetime, Depends(clock)]


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post("", response_model=SkillCreated, status_code=201)
async def create_skill(body: SkillCreate, current: CurrentUserDep, db: Db) -> SkillCreated:
    """Adds a skill to the reference list. Its level will be established by its evidence."""
    skill_id = await SkillsService(db, current.id).create(body)
    await db.commit()
    return SkillCreated(id=skill_id)


@router.get("/graph", response_model=SkillGraphOut)
async def get_graph(current: CurrentUserDep, db: Db, response: Response) -> SkillGraphOut:
    """Skills (nodes), prerequisites (links) and radar per domain. `demand` is `null` until
    the market Radar (phase 8)."""
    _no_store(response)
    return await skill_graph(db, current.id)


@router.get("/compare", response_model=CompareOut)
async def get_compare(
    current: CurrentUserDep,
    db: Db,
    response: Response,
    target: CompareTarget = "goal",
    goal_id: Annotated[str | None, Query(max_length=64)] = None,
    posting_id: Annotated[str | None, Query(max_length=64)] = None,
) -> CompareOut:
    """Me against the target job (`goal`: the skills of the program of goal `goal_id`, otherwise
    of the most recent one that has a program) or against a posting (`posting`: its learnable
    skills, `posting_id` required, otherwise 422 `posting_id_required`), expected at
    `validated`. 404 `goal_not_found`, `posting_not_found` or `no_compare_target`."""
    _no_store(response)
    return await compare_with(db, current.id, target, goal_id=goal_id, posting_id=posting_id)


@router.get("/history", response_model=HistoryOut)
async def get_history(
    current: CurrentUserDep,
    db: Db,
    response: Response,
    now: NowDep,
    weeks: Annotated[int, Query(ge=1, le=MAX_WEEKS)] = DEFAULT_WEEKS,
) -> HistoryOut:
    """Weekly snapshots of the last `weeks` weeks, plus the current week live."""
    _no_store(response)
    return await skill_history(db, current.id, weeks, now)


@router.get("/{skill_id}", response_model=SkillDetailOut)
async def get_skill(
    skill_id: str, current: CurrentUserDep, db: Db, response: Response, now: NowDep
) -> SkillDetailOut:
    """Detail of a skill: evidence, ready postings that cite it (10 at most), next action.
    404 `skill_not_found`."""
    _no_store(response)
    return await skill_detail(db, current.id, skill_id, now)

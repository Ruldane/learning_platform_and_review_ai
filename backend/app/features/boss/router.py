"""Le défi d'un programme est ouvert et remis depuis l'interface."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db
from app.features.boss.schemas import BossAttemptOut, BossProgramOut, BossReviewStarted
from app.features.boss.service import DEFAULT_CLOCK, BossService, Clock
from app.features.boss.service.submission import launch_review

router = APIRouter(prefix="/boss/programs", tags=["boss"])
ProgramId = Annotated[str, Path(min_length=36, max_length=36)]


def _clock(request: Request) -> Clock:
    return getattr(request.app.state, "boss_clock", DEFAULT_CLOCK)


BossClock = Annotated[Clock, Depends(_clock)]


@router.get("/{program_id}")
async def get_boss(
    program_id: ProgramId, db: Db, user: CurrentUserDep, clock: BossClock
) -> BossProgramOut:
    return await BossService(db, user.id, clock).read(program_id)


@router.post("/{program_id}", status_code=201)
async def start_boss(
    program_id: ProgramId, db: Db, user: ConfirmedUserDep, clock: BossClock
) -> BossAttemptOut:
    return await BossService(db, user.id, clock).start(program_id)


@router.post("/{program_id}/submit", status_code=202)
async def submit_boss(
    program_id: ProgramId, request: Request, user: ConfirmedUserDep, clock: BossClock
) -> BossReviewStarted:
    return await launch_review(request.app.state.launcher, user.id, program_id, clock)

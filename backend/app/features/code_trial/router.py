from typing import Annotated

from fastapi import APIRouter, Path, Request

from app.core.deps import CurrentUserDep, Db, InterfaceUserDep
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.features.code_trial.schemas import TrialOpened, TrialVerdict, TrialView
from app.features.code_trial.service import open_trial, read_trial, save_verdict

router = APIRouter(
    prefix="/ide/sessions/{session_id}/code-trials",
    tags=["code_trial"],
    route_class=FieldPathsRoute,
)
Id = Annotated[str, Path(min_length=1, max_length=36)]


@router.get("")
async def latest_trial(session_id: Id, db: Db, user: CurrentUserDep) -> TrialView | None:
    return await read_trial(db, user.id, session_id)


@router.post("", status_code=202)
async def start_trial(
    session_id: Id, request: Request, db: Db, user: CurrentUserDep
) -> TrialOpened:
    return await open_trial(request.app.state.launcher, db, user.id, session_id)


@router.get("/{trial_id}")
async def get_trial(session_id: Id, trial_id: Id, db: Db, user: CurrentUserDep) -> TrialView:
    view = await read_trial(db, user.id, session_id, trial_id)
    if view is None:
        raise AppError("code_trial_not_found", "Procès introuvable.", 404)
    return view


@router.put("/{trial_id}/verdict")
async def decide_trial(
    session_id: Id, trial_id: Id, body: TrialVerdict, db: Db, user: InterfaceUserDep
) -> TrialView:
    return await save_verdict(db, user.id, session_id, trial_id, body)

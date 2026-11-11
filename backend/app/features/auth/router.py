from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep, Db
from app.features.auth.schemas import MeOut
from app.features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=MeOut)
async def me(request: Request, current: CurrentUserDep, db: Db) -> MeOut:
    user = await AuthService(db).get_user(current.id)
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        auth_mode=request.app.state.settings.auth_mode,
    )

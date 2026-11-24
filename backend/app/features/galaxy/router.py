from fastapi import APIRouter, Response

from app.core.deps import CurrentUserDep, Db
from app.features.galaxy.schemas import GalaxyView
from app.features.galaxy.service import read_galaxy

router = APIRouter(prefix="/galaxy", tags=["galaxy"])


@router.get("")
async def get_galaxy(current: CurrentUserDep, db: Db, response: Response) -> GalaxyView:
    """The skill map and the active notes visible to the account."""
    response.headers["Cache-Control"] = "no-store"
    return await read_galaxy(db, current.id)

from fastapi import APIRouter, Response

from app.core.deps import CurrentUserDep, Db
from app.features.galaxy.schemas import GalaxyView
from app.features.galaxy.service import read_galaxy

router = APIRouter(prefix="/galaxy", tags=["galaxy"])


@router.get("")
async def get_galaxy(current: CurrentUserDep, db: Db, response: Response) -> GalaxyView:
    """La carte des compétences et des notes actives visibles par le compte."""
    response.headers["Cache-Control"] = "no-store"
    return await read_galaxy(db, current.id)

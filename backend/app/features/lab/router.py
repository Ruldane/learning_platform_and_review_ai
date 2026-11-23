from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.features.lab import service
from app.features.lab.overview import router as overview_router
from app.features.lab.schemas import LabPreferences, LabPreferencesPatch

router = APIRouter(prefix="/lab", tags=["lab"])
router.include_router(overview_router)


@router.get("/preferences", response_model=LabPreferences)
async def read(db: Db, current: CurrentUserDep) -> LabPreferences:
    return await service.preferences(db, current.id)


@router.patch("/preferences", response_model=LabPreferences)
async def change(db: Db, current: CurrentUserDep, body: LabPreferencesPatch) -> LabPreferences:
    return await service.change_preferences(db, current.id, body)

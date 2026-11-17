from fastapi import APIRouter

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.settings.schemas import SettingsOut, UserSettings
from app.features.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"], route_class=FieldPathsRoute)


@router.get("", response_model=SettingsOut)
async def get_settings(current: CurrentUserDep, db: Db) -> SettingsOut:
    return SettingsOut.of(await SettingsService(db, current.id).get(initialize=True))


@router.put("", response_model=SettingsOut)
async def replace_settings(body: UserSettings, current: CurrentUserDep, db: Db) -> SettingsOut:
    return SettingsOut.of(await SettingsService(db, current.id).replace(body))

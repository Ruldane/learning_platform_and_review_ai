from sqlalchemy.ext.asyncio import AsyncSession

from app.features.lab.navigation import NAVIGATION as NAVIGATION
from app.features.lab.repository import LabPreferencesRepository
from app.features.lab.schemas import LabPreferences, LabPreferencesPatch


async def preferences(db: AsyncSession, user_id: str) -> LabPreferences:
    row = await LabPreferencesRepository(db, user_id).read()
    return LabPreferences.model_validate(row) if row else LabPreferences()


async def change_preferences(
    db: AsyncSession, user_id: str, patch: LabPreferencesPatch
) -> LabPreferences:
    repo = LabPreferencesRepository(db, user_id)
    if patch.pinned is None and patch.tour is None:
        return await preferences(db, user_id)
    row = await repo.locked()
    if row is None:
        row = await repo.add(pinned=patch.pinned or [], tour=patch.tour or "pending")
    else:
        if patch.pinned is not None:
            row.pinned = patch.pinned
        if patch.tour is not None:
            row.tour = patch.tour
    await db.flush()
    return LabPreferences.model_validate(row)

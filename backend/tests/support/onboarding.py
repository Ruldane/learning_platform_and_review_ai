"""Premier lancement des comptes de test (D183, D197) : le planificateur ne traite que les comptes
dont `onboarding_done` est vrai ; les tests qui l'exercent les marquent « faits » avec ce geste."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import UserSettingsRow
from app.features.settings.service import SettingsService


async def finish_first_launch(
    factory: async_sessionmaker[AsyncSession], *user_ids: str, done: bool = True
) -> None:
    """Enregistre les réglages par défaut de chaque compte, avec `onboarding_done = done` (sans
    jamais le défaire, comme la route)."""
    async with factory() as db:
        for user_id in user_ids:
            service = SettingsService(db, user_id)
            current = await service.get(initialize=True)
            await service.replace(current.model_copy(update={"onboarding_done": done}))
        await db.commit()


async def hold_first_launch(factory: async_sessionmaker[AsyncSession], user_id: str) -> None:
    """Un compte en plein premier lancement alors qu'il a déjà des données : sa ligne de réglages
    (`onboarding_done = false`) existe avant elles, comme au premier `GET /settings`."""
    async with factory() as db:
        db.add(UserSettingsRow(user_id=user_id, data={"onboarding_done": False}))
        await db.commit()

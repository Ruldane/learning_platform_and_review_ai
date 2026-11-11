from typing import Any

from app.db.models.accounts import UserSettingsRow
from app.db.repository import UserScopedRepository


class UserSettingsRepository(UserScopedRepository[UserSettingsRow]):
    """Une seule ligne `user_settings` par utilisateur (contrainte d'unicité sur `user_id`)."""

    model = UserSettingsRow

    async def _row(self) -> UserSettingsRow | None:
        rows = await self.list()
        return rows[0] if rows else None

    async def get_data(self) -> dict[str, Any] | None:
        row = await self._row()
        return row.data if row is not None else None

    async def save_data(self, data: dict[str, Any]) -> None:
        # La colonne JSON n'est pas suivie en profondeur : on affecte toujours un nouveau dict.
        row = await self._row()
        if row is None:
            await self.add(data=dict(data))
        else:
            await self.update(row.id, data=dict(data))

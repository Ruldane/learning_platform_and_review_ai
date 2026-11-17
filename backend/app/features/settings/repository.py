from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.dialects.sqlite import insert

from app.db.base import new_id
from app.db.models.accounts import ApiKey, UserSettingsRow
from app.db.models.learning import Goal
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

    async def has_prior_data(self) -> bool:
        """Vrai si le compte a déjà une clé d'API enregistrée ou un objectif : il s'en est déjà
        servi, il n'a pas de premier lancement à faire (P20)."""
        key = select(ApiKey.id).where(ApiKey.user_id == self.user_id)
        goal = select(Goal.id).where(Goal.user_id == self.user_id)
        found = await self.session.execute(select(or_(exists(key), exists(goal))))
        return bool(found.scalar())

    async def initialize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Crée la ligne si elle n'existe pas encore, sans jamais écraser celle qu'une requête
        simultanée vient de créer (un seul `INSERT` gagne, l'autre ne fait rien) ; rend les
        données qui sont en base."""
        now = datetime.now(UTC)
        stmt = insert(UserSettingsRow).values(
            id=new_id(), user_id=self.user_id, data=dict(data), created_at=now, updated_at=now
        )
        await self.session.execute(stmt.on_conflict_do_nothing(index_elements=["user_id"]))
        # Lecture de la colonne seule : l'ORM ne doit pas garder une ligne écrite hors de lui.
        read = select(UserSettingsRow.data).where(UserSettingsRow.user_id == self.user_id)
        stored = (await self.session.execute(read)).scalar_one_or_none()
        return stored if isinstance(stored, dict) else dict(data)

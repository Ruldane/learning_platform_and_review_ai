"""Journal (SPEC F18) : les écritures passent par `INSERT … ON CONFLICT DO NOTHING`, pour qu'un
rejeu (ou deux requêtes simultanées) de la même `ref_key` ne lève jamais d'erreur d'unicité."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.study import JournalEntry
from app.db.repository import UserScopedRepository


class JournalRepository(UserScopedRepository[JournalEntry]):
    model = JournalEntry

    async def insert_once(self, ref_key: str | None, **fields: Any) -> str:
        """Écrit la ligne et rend son id ; si `ref_key` existe déjà pour cet utilisateur, rend
        l'id de la ligne existante sans rien changer. Sans `ref_key`, la ligne est toujours
        neuve."""
        stmt = (
            sqlite_insert(JournalEntry)
            .values(user_id=self.user_id, ref_key=ref_key, **fields)
            .on_conflict_do_nothing(index_elements=["user_id", "ref_key"])
            .returning(JournalEntry.id)
        )
        created = (await self.session.execute(stmt)).scalar_one_or_none()
        if created is not None:
            return created
        existing = select(JournalEntry.id).where(
            JournalEntry.user_id == self.user_id, JournalEntry.ref_key == ref_key
        )
        return (await self.session.execute(existing)).scalar_one()

"""Journal (SPEC F18) : les écritures passent par `INSERT … ON CONFLICT DO NOTHING`, pour qu'un
rejeu (ou deux requêtes simultanées) de la même `ref_key` ne lève jamais d'erreur d'unicité. La
lecture va de la plus récente à la plus ancienne (`created_at`, puis ordre d'insertion)."""

import builtins
from typing import Any

from sqlalchemy import ColumnElement, and_, literal_column, or_, select
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

    async def by_ref(self, ref_key: str) -> JournalEntry | None:
        stmt = select(JournalEntry).where(
            JournalEntry.user_id == self.user_id, JournalEntry.ref_key == ref_key
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def page(
        self, kind: str | None, before: str | None, limit: int
    ) -> builtins.list[JournalEntry] | None:
        """Jusqu'à `limit` lignes, les plus récentes d'abord, plus anciennes que la ligne
        `before` (curseur) ; `None` si ce curseur n'est pas une ligne de l'utilisateur."""
        rowid: ColumnElement[int] = literal_column("rowid")
        stmt = select(JournalEntry).where(JournalEntry.user_id == self.user_id)
        if kind is not None:
            stmt = stmt.where(JournalEntry.kind == kind)
        if before is not None:
            cursor = (
                await self.session.execute(
                    select(JournalEntry.created_at, rowid).where(
                        JournalEntry.user_id == self.user_id, JournalEntry.id == before
                    )
                )
            ).first()
            if cursor is None:
                return None
            at, seq = cursor
            stmt = stmt.where(
                or_(
                    JournalEntry.created_at < at,
                    and_(JournalEntry.created_at == at, rowid < seq),
                )
            )
        stmt = stmt.order_by(JournalEntry.created_at.desc(), rowid.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

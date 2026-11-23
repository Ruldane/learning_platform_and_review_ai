"""Lecture des lignes d'une utilisatrice, table par table.

Exception documentée à `UserScopedRepository` : l'export parcourt **toutes** les tables qui ont
`user_id` (une table de plus n'y change rien), donc il n'a pas de modèle fixe ; chaque lecture
filtre pourtant sur `user_id`, toujours."""

from collections.abc import AsyncGenerator, Sequence
from typing import Any

from sqlalchemy import Column, Select, Table, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import AccountVectorPurge


class AccountRepository:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    def _select(self, table: Table, columns: Sequence[Column[Any]] | None) -> Select[Any]:
        """Les lignes de `user_id` dans l'ordre de leur création puis de leur identifiant. Seules
        les `columns` données sont lues (toutes par défaut) : une colonne écartée n'entre jamais
        en mémoire."""
        stmt = select(*(table.c if columns is None else columns)).where(
            table.c.user_id == self.user_id
        )
        order = [table.c[name] for name in ("created_at", "id") if name in table.c]
        return stmt.order_by(*order)

    async def batches(
        self, table: Table, columns: Sequence[Column[Any]] | None, size: int
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Les lignes de `user_id` par lots d'au plus `size` : jamais plus d'un lot en mémoire,
        quel que soit le volume de la table."""
        stream = await self.session.stream(
            self._select(table, columns).execution_options(yield_per=size)
        )
        try:
            async for batch in stream.mappings().partitions(size):
                yield [dict(row) for row in batch]
        finally:
            await stream.close()

    async def rows(
        self, table: Table, columns: Sequence[Column[Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Toutes les lignes d'un coup, pour une petite table (les sessions d'un compte). L'export
        lit par lots (`batches`)."""
        result = await self.session.execute(self._select(table, columns))
        return [dict(row) for row in result.mappings()]


async def queue_vector_purge(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        insert(AccountVectorPurge)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=[AccountVectorPurge.user_id])
    )


async def complete_vector_purge(db: AsyncSession, user_id: str) -> None:
    await db.execute(delete(AccountVectorPurge).where(AccountVectorPurge.user_id == user_id))


async def pending_vector_purges(db: AsyncSession) -> list[str]:
    """File de travail du planificateur, indépendante des comptes et sans contenu utilisateur."""
    result = await db.scalars(
        select(AccountVectorPurge.user_id).order_by(AccountVectorPurge.created_at)
    )
    return list(result)

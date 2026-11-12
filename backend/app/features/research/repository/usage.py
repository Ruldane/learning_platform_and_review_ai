from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, literal, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow
from app.db.models.research import SearchUsage
from app.db.repository import UserScopedRepository


class SearchUsageRepository(UserScopedRepository[SearchUsage]):
    """Compteur mensuel d'un utilisateur par fournisseur et par clé."""

    model = SearchUsage

    async def increment(self, provider: str, month: str, fingerprint: str) -> None:
        """Ajoute 1 au compteur en une seule instruction : pas de lecture-écriture perdue."""
        stmt = sqlite_insert(SearchUsage).values(
            user_id=self.user_id,
            provider=provider,
            month=month,
            key_fingerprint=fingerprint,
            count=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "provider", "month", "key_fingerprint"],
            set_={"count": SearchUsage.count + 1, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)

    async def reserve(self, provider: str, month: str, fingerprint: str, cap: int) -> bool:
        """Ajoute 1 au compteur de l'utilisateur seulement si le total du mois pour cette clé
        (tous utilisateurs, comme `month_total`) est sous `cap`. Une seule instruction
        `INSERT … SELECT … WHERE total < cap ON CONFLICT DO UPDATE` : SQLite l'exécute sous son
        verrou d'écriture, donc le contrôle et l'ajout sont indivisibles, même entre processus.
        Rend vrai si une requête a été réservée."""
        now: datetime = utcnow()
        values = select(
            literal(new_id()),
            literal(self.user_id),
            literal(provider),
            literal(month),
            literal(fingerprint),
            literal(1),
            literal(now, SearchUsage.created_at.type),
            literal(now, SearchUsage.updated_at.type),
        ).where(_total(provider, month, fingerprint).scalar_subquery() < cap)
        columns = ["id", "user_id", "provider", "month", "key_fingerprint", "count"]
        stmt = sqlite_insert(SearchUsage).from_select(
            [*columns, "created_at", "updated_at"], values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "provider", "month", "key_fingerprint"],
            set_={"count": SearchUsage.count + 1, "updated_at": stmt.excluded.updated_at},
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0) == 1  # type: ignore[attr-defined]

    async def release(self, provider: str, month: str, fingerprint: str) -> bool:
        """Rend une requête réservée que le fournisseur n'a pas servie : `count - 1` sur la
        seule ligne de l'utilisateur, en une instruction gardée par `count > 0` (jamais
        négatif, jamais sur le compte d'un autre). Rend vrai si une requête a été rendue."""
        stmt = (
            update(SearchUsage)
            .where(
                SearchUsage.user_id == self.user_id,
                SearchUsage.provider == provider,
                SearchUsage.month == month,
                SearchUsage.key_fingerprint == fingerprint,
                SearchUsage.count > 0,
            )
            .values(count=SearchUsage.count - 1, updated_at=utcnow())
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0) == 1  # type: ignore[attr-defined]


def _total(provider: str, month: str, fingerprint: str) -> Select[Any]:
    return select(func.coalesce(func.sum(SearchUsage.count), 0)).where(
        SearchUsage.provider == provider,
        SearchUsage.month == month,
        SearchUsage.key_fingerprint == fingerprint,
    )


async def month_total(db: AsyncSession, *, provider: str, month: str, fingerprint: str) -> int:
    """Requêtes du mois pour une même clé, tous utilisateurs confondus (D75).

    Seule lecture de la phase sans filtre `user_id` : une clé `.env` est partagée par tous les
    utilisateurs en mode Google, et son plafond est celui du compte Brave, pas d'un utilisateur.
    Ne renvoie qu'un nombre, jamais une ligne ni un identifiant d'utilisateur.
    """
    return int((await db.execute(_total(provider, month, fingerprint))).scalar_one())

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

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


async def month_total(db: AsyncSession, *, provider: str, month: str, fingerprint: str) -> int:
    """Requêtes du mois pour une même clé, tous utilisateurs confondus (D75).

    Seule lecture de la phase sans filtre `user_id` : une clé `.env` est partagée par tous les
    utilisateurs en mode Google, et son plafond est celui du compte Brave, pas d'un utilisateur.
    Ne renvoie qu'un nombre, jamais une ligne ni un identifiant d'utilisateur.
    """
    stmt = select(func.coalesce(func.sum(SearchUsage.count), 0)).where(
        SearchUsage.provider == provider,
        SearchUsage.month == month,
        SearchUsage.key_fingerprint == fingerprint,
    )
    return int((await db.execute(stmt)).scalar_one())

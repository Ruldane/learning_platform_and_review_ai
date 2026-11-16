"""Briefs d'un utilisateur (13.6) et lectures des liens déjà connus. Les écritures disputées sont
gardées en SQL (`INSERT … ON CONFLICT DO NOTHING`, `UPDATE … WHERE` sur l'état attendu) : deux
requêtes ou deux tâches ne créent jamais deux briefs pour un jour, et la première écriture d'une
rubrique gagne. Le commit appartient à l'appelant."""

import builtins
from datetime import date, datetime
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.applications import Application
from app.db.models.daily import Brief
from app.db.models.postings import JobPosting
from app.db.repository import UserScopedRepository


def _changed(result: Any) -> bool:
    return isinstance(result, CursorResult) and result.rowcount == 1


class BriefRepository(UserScopedRepository[Brief]):
    model = Brief

    async def get_fresh(self, brief_id: str) -> Brief | None:
        stmt = (
            select(Brief)
            .where(Brief.id == brief_id, Brief.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_day(self, day: date) -> Brief | None:
        stmt = (
            select(Brief)
            .where(Brief.user_id == self.user_id, Brief.day == day)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def before(self, day: date, limit: int) -> builtins.list[Brief]:
        """Les briefs des jours précédant `day`, le plus récent d'abord."""
        stmt = (
            select(Brief)
            .where(Brief.user_id == self.user_id, Brief.day < day)
            .order_by(Brief.day.desc())
            .limit(limit)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def insert_if_absent(
        self,
        *,
        day: date,
        origin: str,
        sections: dict[str, Any],
        offer_keys: builtins.list[str],
        now: datetime,
    ) -> str | None:
        """Crée le brief du jour et rend son id ; `None` si ce jour a déjà son brief (rien n'est
        changé). Seul celui qui reçoit un id lance la session du conseil."""
        stmt = (
            sqlite_insert(Brief)
            .values(
                user_id=self.user_id,
                day=day,
                origin=origin,
                sections=sections,
                offer_keys=offer_keys,
                advice_status="pending",
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
            .returning(Brief.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _update_where(self, brief_id: str, *where: Any, **values: Any) -> bool:
        stmt = (
            update(Brief)
            .where(Brief.id == brief_id, Brief.user_id == self.user_id, *where)
            .values(**values)
        )
        return _changed(await self.session.execute(stmt))

    async def set_session(self, brief_id: str, session_id: str) -> bool:
        return await self._update_where(brief_id, Brief.session_id.is_(None), session_id=session_id)

    async def save_resource(self, brief_id: str, resource: dict[str, Any]) -> bool:
        """Première écriture gagnante : `{}` est la rubrique vide (rangée, sans ressource)."""
        return await self._update_where(brief_id, Brief.resource.is_(None), resource=resource)

    async def save_advice(self, brief_id: str, advice: dict[str, Any]) -> bool:
        return await self._update_where(
            brief_id,
            Brief.advice.is_(None),
            Brief.advice_status == "pending",
            advice=advice,
            advice_status="ready",
        )

    async def close_advice(self, brief_id: str, status: str) -> bool:
        """Le conseil `failed` ou `unavailable`, seulement s'il est encore `pending` : définitif."""
        return await self._update_where(
            brief_id, Brief.advice_status == "pending", advice_status=status
        )

    async def known_keys(self) -> builtins.set[str]:
        """Les liens normalisés des offres et des fiches déjà saisies."""
        keys: builtins.set[str] = set()
        for model in (JobPosting, Application):
            stmt = select(model.url_norm).where(
                model.user_id == self.user_id, model.url_norm.is_not(None)
            )
            keys.update(str(key) for key in (await self.session.execute(stmt)).scalars())
        return keys

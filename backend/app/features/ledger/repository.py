"""Registre persistant des passages planifiés (P13) : une ligne par `(user_id, name, period)`.

Les écritures disputées sont gardées en SQL, pour que deux processus ou deux tâches ne gagnent
jamais le même passage : `INSERT … ON CONFLICT DO NOTHING`, puis `UPDATE … WHERE` sur l'état
attendu (statut, nombre d'essais). Le commit appartient à l'appelant. `all_user_ids` est la seule
lecture sans `user_id` du registre (D18, D91) : elle sert aux tâches planifiées."""

from datetime import datetime
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import User
from app.db.models.daily import JobRun
from app.db.repository import UserScopedRepository


def _changed(result: Any) -> bool:
    return isinstance(result, CursorResult) and result.rowcount == 1


async def all_user_ids(db: AsyncSession) -> list[str]:
    """Les identifiants de tous les comptes (tâches planifiées seulement)."""
    stmt = select(User.id).order_by(User.created_at, User.id)
    return list((await db.execute(stmt)).scalars())


class JobRunRepository(UserScopedRepository[JobRun]):
    model = JobRun

    async def insert_running(self, name: str, period: str, now: datetime) -> str | None:
        """Crée le passage `running` (essai 1) et rend son id ; `None` si la période a déjà sa
        ligne (rien n'est changé)."""
        stmt = (
            sqlite_insert(JobRun)
            .values(
                user_id=self.user_id, name=name, period=period, status="running", started_at=now
            )
            .on_conflict_do_nothing(index_elements=["user_id", "name", "period"])
            .returning(JobRun.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_period(self, name: str, period: str) -> JobRun | None:
        stmt = (
            select(JobRun)
            .where(JobRun.user_id == self.user_id, JobRun.name == name, JobRun.period == period)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def reclaim(self, run_id: str, old_attempts: int, now: datetime) -> bool:
        """Reprend un passage `failed` ou `running` : essai suivant, seulement si personne ne l'a
        déjà repris (`attempts` inchangé) ni terminé."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.attempts == old_attempts,
                JobRun.status.in_(("failed", "running")),
            )
            .values(
                status="running",
                started_at=now,
                finished_at=None,
                error_code=None,
                attempts=old_attempts + 1,
                updated_at=now,
            )
        )
        return _changed(await self.session.execute(stmt))

    async def close_running(self, run_id: str, attempt: int, now: datetime, **values: Any) -> bool:
        """Termine l'essai `attempt` d'un passage encore `running` (jamais un passage déjà fini,
        ni d'un autre, ni un essai repris depuis : un ouvrier périmé ne ferme pas l'essai
        suivant)."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.status == "running",
                JobRun.attempts == attempt,
            )
            .values(finished_at=now, updated_at=now, **values)
        )
        return _changed(await self.session.execute(stmt))

    async def reopen_done(self, run_id: str, attempt: int, now: datetime, code: str) -> bool:
        """Un passage `done` dont le travail lancé a échoué repasse en `failed` (essai
        `attempt` seulement) : `claim` peut le reprendre, dans la limite des essais."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.status == "done",
                JobRun.attempts == attempt,
            )
            .values(status="failed", error_code=code, updated_at=now)
        )
        return _changed(await self.session.execute(stmt))

    async def abandon(self, run_id: str, old_attempts: int, now: datetime) -> bool:
        """Un passage `running` périmé, sans essai restant : il passe en `failed`
        (`abandoned`), pour apparaître au fil au lieu de rester « en cours »."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.attempts == old_attempts,
                JobRun.status == "running",
            )
            .values(status="failed", finished_at=now, error_code="abandoned", updated_at=now)
        )
        return _changed(await self.session.execute(stmt))

    async def last_done(self, name: str) -> JobRun | None:
        stmt = (
            select(JobRun)
            .where(
                JobRun.user_id == self.user_id,
                JobRun.name == name,
                JobRun.status == "done",
                JobRun.finished_at.is_not(None),
            )
            .order_by(JobRun.finished_at.desc(), JobRun.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def failures(
        self, after: datetime | None, before: datetime | None, limit: int
    ) -> list[JobRun]:
        """Les passages en échec finis dans `[after, before]` (bornes incluses : le fil rend les
        ex æquo, il en écarte lui-même), le plus récent d'abord."""
        stmt = select(JobRun).where(JobRun.user_id == self.user_id, JobRun.status == "failed")
        if after is not None:
            stmt = stmt.where(JobRun.finished_at >= after)
        if before is not None:
            stmt = stmt.where(JobRun.finished_at <= before)
        stmt = stmt.order_by(JobRun.finished_at.desc(), JobRun.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars())

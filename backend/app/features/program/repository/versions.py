import builtins

from sqlalchemy import ColumnElement, func, or_, select

from app.db.models.program import PlanVersion
from app.db.repository import UserScopedRepository


def _applied() -> ColumnElement[bool]:
    """Versions qui décrivent des lignes écrites : celles du Stratège et de January (`build`,
    écrites dès leur rangement) et les replanifications acceptées. Une proposition `replan`
    en attente, refusée, remplacée ou close n'a jamais touché le plan (F2, D106)."""
    return or_(PlanVersion.kind == "build", PlanVersion.status == "accepted")


class PlanVersionRepository(UserScopedRepository[PlanVersion]):
    """Versions d'un programme : instantané, différence, raison, date d'acceptation."""

    model = PlanVersion

    async def by_revision(self, session_id: str, revision: int) -> PlanVersion | None:
        """La version écrite par cette révision du Stratège (idempotence au rejeu)."""
        stmt = (
            select(PlanVersion)
            .where(
                PlanVersion.user_id == self.user_id,
                PlanVersion.session_id == session_id,
                PlanVersion.revision == revision,
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest(self, program_id: str) -> PlanVersion | None:
        """La dernière version appliquée au plan (jamais une proposition non acceptée)."""
        stmt = (
            select(PlanVersion)
            .where(
                PlanVersion.user_id == self.user_id,
                PlanVersion.program_id == program_id,
                _applied(),
            )
            .order_by(PlanVersion.version.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_with_catalog(self, program_id: str) -> PlanVersion | None:
        """La dernière version du Stratège (son instantané porte le référentiel)."""
        stmt = (
            select(PlanVersion)
            .where(
                PlanVersion.user_id == self.user_id,
                PlanVersion.program_id == program_id,
                PlanVersion.revision.is_not(None),
                PlanVersion.kind == "build",
            )
            .order_by(PlanVersion.version.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def supersede_pending(self, program_id: str, keep: str | None = None) -> None:
        """Passe à `superseded` les propositions en attente du programme, sauf `keep` : une
        version `pending` qu'une plus récente remplace ne doit plus pouvoir être acceptée."""
        stmt = select(PlanVersion).where(
            PlanVersion.user_id == self.user_id,
            PlanVersion.program_id == program_id,
            PlanVersion.status == "pending",
        )
        for row in (await self.session.execute(stmt)).scalars():
            if row.id != keep:
                row.status = "superseded"
        await self.session.flush()

    async def next_version(self, program_id: str) -> int:
        stmt = select(func.max(PlanVersion.version)).where(
            PlanVersion.user_id == self.user_id, PlanVersion.program_id == program_id
        )
        current = (await self.session.execute(stmt)).scalar_one_or_none()
        return 1 if current is None else int(current) + 1

    async def by_number(self, program_id: str, version: int) -> PlanVersion | None:
        stmt = (
            select(PlanVersion)
            .where(
                PlanVersion.user_id == self.user_id,
                PlanVersion.program_id == program_id,
                PlanVersion.version == version,
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def history(self, program_id: str) -> builtins.list[PlanVersion]:
        """Toutes les versions du programme, la plus récente d'abord."""
        stmt = (
            select(PlanVersion)
            .where(PlanVersion.user_id == self.user_id, PlanVersion.program_id == program_id)
            .order_by(PlanVersion.version.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

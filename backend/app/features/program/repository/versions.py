import builtins

from sqlalchemy import ColumnElement, func, or_, select

from app.db.models.program import PlanVersion
from app.db.repository import UserScopedRepository


def _applied() -> ColumnElement[bool]:
    """Versions that describe written rows: those of the Strategist and of January (`build`, written
    as soon as they are stored) and the accepted replans. A `replan` proposal that is pending,
    refused, replaced or closed never touched the plan (F2, D106)."""
    return or_(PlanVersion.kind == "build", PlanVersion.status == "accepted")


class PlanVersionRepository(UserScopedRepository[PlanVersion]):
    """Versions of a program: snapshot, diff, reason, acceptance date."""

    model = PlanVersion

    async def by_revision(self, session_id: str, revision: int) -> PlanVersion | None:
        """The version written by this revision of the Strategist (idempotent on replay)."""
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
        """The latest version applied to the plan (never an unaccepted proposal)."""
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
        """The latest Strategist version (its snapshot holds the reference data)."""
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
        """Moves the pending proposals of the program to `superseded`, except `keep`: a `pending`
        version that a newer one replaces must no longer be acceptable."""
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
        """All versions of the program, most recent first."""
        stmt = (
            select(PlanVersion)
            .where(PlanVersion.user_id == self.user_id, PlanVersion.program_id == program_id)
            .order_by(PlanVersion.version.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

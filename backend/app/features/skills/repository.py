"""January's skill graph (SPEC 13.4): skills, prerequisite links, levels.

Creations go through `INSERT … ON CONFLICT DO NOTHING`: two simultaneous validations that create
the same skill (same `norm_name`) never raise a uniqueness error."""

import builtins
from collections.abc import Collection
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.skills import Skill, SkillEdge, SkillSnapshot, UserSkill
from app.db.repository import UserScopedRepository


class SkillRepository(UserScopedRepository[Skill]):
    model = Skill

    async def ensure(
        self, name: str, norm_name: str, domain: str | None, synonyms: list[Any]
    ) -> None:
        """Creates the skill if its normalized name is new."""
        stmt = sqlite_insert(Skill).values(
            user_id=self.user_id,
            name=name,
            norm_name=norm_name,
            domain=domain,
            synonyms=synonyms,
        )
        await self.session.execute(
            stmt.on_conflict_do_nothing(index_elements=["user_id", "norm_name"])
        )

    async def create(
        self, name: str, norm_name: str, domain: str | None, synonyms: list[str]
    ) -> str | None:
        """Adds the row through the ORM so that it can be undone from the MCP history."""
        try:
            row = await self.add(name=name, norm_name=norm_name, domain=domain, synonyms=synonyms)
        except IntegrityError:
            # the route's transaction contains only this insertion.
            await self.session.rollback()
            if not await self.by_norm([norm_name]):
                raise
            return None
        return row.id

    async def by_norm(self, norm_names: Collection[str]) -> dict[str, Skill]:
        if not norm_names:
            return {}
        stmt = (
            select(Skill)
            .where(Skill.user_id == self.user_id, Skill.norm_name.in_(builtins.list(norm_names)))
            .execution_options(populate_existing=True)
        )
        return {row.norm_name: row for row in (await self.session.execute(stmt)).scalars()}

    async def list_all(self) -> builtins.list[Skill]:
        """All of January's skills, re-read (the map has no cache, F15)."""
        stmt = (
            select(Skill)
            .where(Skill.user_id == self.user_id)
            .order_by(Skill.name, Skill.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class SkillEdgeRepository(UserScopedRepository[SkillEdge]):
    model = SkillEdge

    async def ensure(self, before_id: str, after_id: str) -> None:
        stmt = sqlite_insert(SkillEdge).values(
            user_id=self.user_id, before_id=before_id, after_id=after_id
        )
        await self.session.execute(
            stmt.on_conflict_do_nothing(index_elements=["before_id", "after_id"])
        )

    async def pairs(self) -> builtins.list[tuple[str, str]]:
        """`(before, after)` of each prerequisite link of January's."""
        stmt = (
            select(SkillEdge.before_id, SkillEdge.after_id)
            .where(SkillEdge.user_id == self.user_id)
            .order_by(SkillEdge.before_id, SkillEdge.after_id)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]


class UserSkillRepository(UserScopedRepository[UserSkill]):
    model = UserSkill

    async def ensure(self, skill_id: str, level: str) -> None:
        """Creates the level if it does not exist (otherwise nothing: `raise_levels` re-reads it and
        raises it)."""
        stmt = sqlite_insert(UserSkill).values(
            user_id=self.user_id, skill_id=skill_id, level=level, evidence=[]
        )
        await self.session.execute(
            stmt.on_conflict_do_nothing(index_elements=["user_id", "skill_id"])
        )

    async def for_skills(self, skill_ids: Collection[str]) -> dict[str, UserSkill]:
        if not skill_ids:
            return {}
        stmt = (
            select(UserSkill)
            .where(
                UserSkill.user_id == self.user_id,
                UserSkill.skill_id.in_(builtins.list(skill_ids)),
            )
            .execution_options(populate_existing=True)
        )
        return {row.skill_id: row for row in (await self.session.execute(stmt)).scalars()}

    async def levels(self) -> builtins.list[tuple[str, str]]:
        """`(normalized name, level)` of each skill January has a level in."""
        stmt = (
            select(Skill.norm_name, UserSkill.level)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .where(Skill.user_id == self.user_id, UserSkill.user_id == self.user_id)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]

    async def by_skill(self) -> dict[str, str]:
        """`skill → level` of all of January's skills."""
        stmt = select(UserSkill.skill_id, UserSkill.level).where(UserSkill.user_id == self.user_id)
        return {row[0]: row[1] for row in (await self.session.execute(stmt)).all()}

    async def rows(self) -> dict[str, UserSkill]:
        """`skill → level row` (level and proofs), re-read."""
        stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return {row.skill_id: row for row in (await self.session.execute(stmt)).scalars()}


class SkillSnapshotRepository(UserScopedRepository[SkillSnapshot]):
    model = SkillSnapshot

    async def insert_once(self, week_start: date, levels: dict[str, str]) -> bool:
        """The week's snapshot, if it does not exist yet (otherwise nothing: the first one wins);
        returns true if it has just been written."""
        stmt = (
            sqlite_insert(SkillSnapshot)
            .values(user_id=self.user_id, week_start=week_start, levels=levels)
            .on_conflict_do_nothing(index_elements=["user_id", "week_start"])
            .returning(SkillSnapshot.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def between(self, first: date, before: date) -> builtins.list[SkillSnapshot]:
        """Snapshots of the weeks from `first` (included) to `before` (excluded), in order."""
        stmt = (
            select(SkillSnapshot)
            .where(
                SkillSnapshot.user_id == self.user_id,
                SkillSnapshot.week_start >= first,
                SkillSnapshot.week_start < before,
            )
            .order_by(SkillSnapshot.week_start)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


async def users_with_levels(session: AsyncSession) -> builtins.list[str]:
    """Users who have at least one skill level, identifiers only.

    Read without `user_id` (D18, D91, D106), reserved for the scheduled snapshots task
    (`app.scheduler`), which then writes each snapshot under its user."""
    stmt = select(UserSkill.user_id).distinct().order_by(UserSkill.user_id)
    return [str(user_id) for user_id in (await session.execute(stmt)).scalars()]

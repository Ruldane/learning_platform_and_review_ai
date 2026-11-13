"""Graphe de compétences de January (SPEC 13.4) : compétences, liens de prérequis, niveaux.

Les créations passent par `INSERT … ON CONFLICT DO NOTHING` : deux validations simultanées qui
créent la même compétence (même `norm_name`) ne lèvent jamais d'erreur d'unicité."""

import builtins
from collections.abc import Collection
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.skills import Skill, SkillEdge, SkillSnapshot, UserSkill
from app.db.repository import UserScopedRepository


class SkillRepository(UserScopedRepository[Skill]):
    model = Skill

    async def ensure(
        self, name: str, norm_name: str, domain: str | None, synonyms: list[Any]
    ) -> None:
        """Crée la compétence si son nom normalisé est nouveau ; sinon rien (la première gagne)."""
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
        """Toutes les compétences de January, relues (la carte n'a aucun cache, F15)."""
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
        """`(avant, après)` de chaque lien de prérequis de January."""
        stmt = (
            select(SkillEdge.before_id, SkillEdge.after_id)
            .where(SkillEdge.user_id == self.user_id)
            .order_by(SkillEdge.before_id, SkillEdge.after_id)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]


class UserSkillRepository(UserScopedRepository[UserSkill]):
    model = UserSkill

    async def ensure(self, skill_id: str, level: str) -> None:
        """Crée le niveau s'il n'existe pas (sinon rien : `raise_levels` le relit et le monte)."""
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
        """`(nom normalisé, niveau)` de chaque compétence dont January a un niveau."""
        stmt = (
            select(Skill.norm_name, UserSkill.level)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .where(Skill.user_id == self.user_id, UserSkill.user_id == self.user_id)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]

    async def by_skill(self) -> dict[str, str]:
        """`compétence → niveau` de toutes les compétences de January."""
        stmt = select(UserSkill.skill_id, UserSkill.level).where(UserSkill.user_id == self.user_id)
        return {row[0]: row[1] for row in (await self.session.execute(stmt)).all()}

    async def rows(self) -> dict[str, UserSkill]:
        """`compétence → ligne de niveau` (niveau et preuves), relues."""
        stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return {row.skill_id: row for row in (await self.session.execute(stmt)).scalars()}


class SkillSnapshotRepository(UserScopedRepository[SkillSnapshot]):
    model = SkillSnapshot

    async def insert_once(self, week_start: date, levels: dict[str, str]) -> bool:
        """Le relevé de la semaine, s'il n'existe pas encore (sinon rien : le premier gagne) ;
        rend vrai s'il vient d'être écrit."""
        stmt = (
            sqlite_insert(SkillSnapshot)
            .values(user_id=self.user_id, week_start=week_start, levels=levels)
            .on_conflict_do_nothing(index_elements=["user_id", "week_start"])
            .returning(SkillSnapshot.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def between(self, first: date, before: date) -> builtins.list[SkillSnapshot]:
        """Relevés des semaines de `first` (compris) à `before` (exclu), dans l'ordre."""
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
    """Les utilisateurs qui ont au moins un niveau de compétence, identifiants seulement.

    Lecture sans `user_id` (D18, D91, D106) réservée à la tâche planifiée des relevés
    (`app.scheduler`), qui écrit ensuite chaque relevé sous son utilisateur."""
    stmt = select(UserSkill.user_id).distinct().order_by(UserSkill.user_id)
    return [str(user_id) for user_id in (await session.execute(stmt)).scalars()]

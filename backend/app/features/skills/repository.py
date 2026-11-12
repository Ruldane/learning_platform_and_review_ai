"""Graphe de compétences de January (SPEC 13.4) : compétences, liens de prérequis, niveaux.

Les créations passent par `INSERT … ON CONFLICT DO NOTHING` : deux validations simultanées qui
créent la même compétence (même `norm_name`) ne lèvent jamais d'erreur d'unicité."""

import builtins
from collections.abc import Collection
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.skills import Skill, SkillEdge, UserSkill
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


class SkillEdgeRepository(UserScopedRepository[SkillEdge]):
    model = SkillEdge

    async def ensure(self, before_id: str, after_id: str) -> None:
        stmt = sqlite_insert(SkillEdge).values(
            user_id=self.user_id, before_id=before_id, after_id=after_id
        )
        await self.session.execute(
            stmt.on_conflict_do_nothing(index_elements=["before_id", "after_id"])
        )


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

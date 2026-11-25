"""Preuves et contrôles, toujours filtrés sur le compte courant."""

from datetime import date

from sqlalchemy import func, select, text

from app.core.errors import AppError
from app.core.skills import Evidence, read_evidence
from app.db.models.skill_transfer import SkillTransfer
from app.db.models.skills import Skill, UserSkill
from app.db.repository import UserScopedRepository


class Transfers(UserScopedRepository[SkillTransfer]):
    model = SkillTransfer

    async def lock_schedule(self) -> None:
        await self.session.execute(text("BEGIN IMMEDIATE"))

    async def count_due(self, day: date) -> int:
        query = (
            select(func.count())
            .select_from(SkillTransfer)
            .where(
                SkillTransfer.user_id == self.user_id,
                SkillTransfer.due_on <= day,
                SkillTransfer.stage.in_(("scheduled", "ready")),
            )
        )
        return int(await self.session.scalar(query) or 0)

    async def get_owned(self, transfer_id: str) -> SkillTransfer:
        found = await self.get(transfer_id)
        if found is None:
            raise AppError("skill_transfer_not_found", "Skill transfer check not found.", 404)
        return found

    async def history(self, skill_id: str | None) -> list[SkillTransfer]:
        query = select(SkillTransfer).where(SkillTransfer.user_id == self.user_id)
        if skill_id is not None:
            query = query.where(SkillTransfer.skill_id == skill_id)
        query = query.order_by(SkillTransfer.due_on.desc(), SkillTransfer.created_at.desc())
        return list((await self.session.scalars(query)).all())

    async def prior_prompts(self, skill_id: str, transfer_id: str) -> tuple[str, ...]:
        query = (
            select(SkillTransfer.exercise)
            .where(
                SkillTransfer.user_id == self.user_id,
                SkillTransfer.skill_id == skill_id,
                SkillTransfer.id != transfer_id,
                SkillTransfer.exercise.is_not(None),
            )
            .order_by(SkillTransfer.created_at.desc())
            .limit(8)
        )
        return tuple(str(value["prompt"]) for value in await self.session.scalars(query) if value)

    async def proofs(self, skill_id: str | None) -> list[tuple[str, str, Evidence]]:
        query = (
            select(Skill.id, Skill.name, UserSkill.evidence)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .where(Skill.user_id == self.user_id, UserSkill.user_id == self.user_id)
            .order_by(Skill.name)
        )
        if skill_id is not None:
            query = query.where(Skill.id == skill_id)
        return [
            (sid, name, item)
            for sid, name, values in (await self.session.execute(query)).all()
            for item in reversed(read_evidence(values))
        ]

    async def schedule(
        self, skill_id: str, proof_id: str, proof: dict[str, object], due_on: date
    ) -> SkillTransfer:
        identity = {
            "skill_id": skill_id,
            "proof_id": proof_id,
            "due_on": due_on,
        }
        query = select(SkillTransfer).filter_by(user_id=self.user_id, **identity)
        existing = await self.session.scalar(query)
        if existing is not None:
            return existing
        return await self.add(**identity, proof=proof, stage="scheduled")

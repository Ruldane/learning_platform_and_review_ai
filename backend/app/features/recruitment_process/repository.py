from sqlalchemy import select

from app.core.errors import AppError
from app.core.skills import normalize_skill_name, read_evidence
from app.db.models.recruitment_process import RecruitmentProcess
from app.db.models.skills import Skill, UserSkill
from app.db.repository import UserScopedRepository

_DIRECT_EVIDENCE = {"quiz", "project", "ide", "github", "system_design", "contribution", "feynman"}


class RecruitmentCases(UserScopedRepository[RecruitmentProcess]):
    model = RecruitmentProcess

    async def require(self, process_id: str) -> RecruitmentProcess:
        row = await self.get(process_id)
        if row is None:
            raise AppError("recruitment_not_found", "Recruitment process not found.", 404)
        return row

    async def history(self) -> list[RecruitmentProcess]:
        query = (
            select(RecruitmentProcess)
            .where(RecruitmentProcess.user_id == self.user_id)
            .order_by(RecruitmentProcess.created_at.desc())
        )
        return list((await self.session.scalars(query)).all())

    async def demonstrated_skills(self) -> set[str]:
        query = (
            select(Skill.norm_name, Skill.synonyms, UserSkill.evidence)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .where(Skill.user_id == self.user_id, UserSkill.user_id == self.user_id)
        )
        return {
            name
            for norm, synonyms, raw in (await self.session.execute(query)).all()
            if any(item["kind"] in _DIRECT_EVIDENCE for item in read_evidence(raw))
            for name in (norm, *(normalize_skill_name(str(synonym)) for synonym in synonyms))
        }

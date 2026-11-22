from sqlalchemy import select, update

from app.agents.tools.code_trial_port import CodePleading
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.db.models.code_trial import CodeTrial
from app.db.repository import UserScopedRepository
from app.features.code_trial.schemas import TrialVerdict


class TrialRepository(UserScopedRepository[CodeTrial]):
    model = CodeTrial

    async def latest(self, project_id: str) -> CodeTrial | None:
        stmt = (
            select(CodeTrial)
            .where(CodeTrial.user_id == self.user_id, CodeTrial.ide_session_id == project_id)
            .order_by(CodeTrial.created_at.desc(), CodeTrial.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def for_version(self, project_id: str, version: int) -> CodeTrial | None:
        stmt = select(CodeTrial).where(
            CodeTrial.user_id == self.user_id,
            CodeTrial.ide_session_id == project_id,
            CodeTrial.files_version == version,
        )
        return await self.session.scalar(stmt)

    async def require(self, trial_id: str) -> CodeTrial:
        row = await self.get(trial_id)
        if row is None:
            raise missing()
        return row

    async def save_pleadings(
        self, trial: CodeTrial, session_id: str, pleadings: list[CodePleading]
    ) -> bool:
        running = select(AgentSession.id).where(
            AgentSession.id == session_id,
            AgentSession.user_id == self.user_id,
            AgentSession.status == "running",
        )
        stmt = (
            update(CodeTrial)
            .where(
                CodeTrial.user_id == self.user_id,
                CodeTrial.id == trial.id,
                CodeTrial.session_id == session_id,
                CodeTrial.pleadings.is_(None),
                running.exists(),
            )
            .values(pleadings=[part.model_dump(mode="json") for part in pleadings])
            .returning(CodeTrial.id)
        )
        return await self.session.scalar(stmt) is not None

    async def set_verdict(self, row: CodeTrial, verdict: TrialVerdict) -> None:
        stmt = (
            update(CodeTrial)
            .where(
                CodeTrial.user_id == self.user_id,
                CodeTrial.id == row.id,
                CodeTrial.pleadings.is_not(None),
                CodeTrial.verdict_choice.is_(None),
            )
            .values(verdict_choice=verdict.choice, verdict_reason=verdict.reason)
        )
        await self.session.execute(stmt)
        await self.session.refresh(row)


def missing() -> AppError:
    return AppError("code_trial_not_found", "Procès introuvable.", 404)

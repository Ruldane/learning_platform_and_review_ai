from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.code_trial_port import CodePassage, CodePleading
from app.core.errors import AppError
from app.db.models.code_trial import CodeTrial
from app.features.code_trial.repository import TrialRepository, missing
from app.features.code_trial.snapshot import excerpts


async def _bound(repo: TrialRepository, trial_id: str, session_id: str) -> CodeTrial:
    row = await repo.require(trial_id)
    if row.session_id != session_id:
        raise missing()
    return row


class AgentCodeTrialStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def passages(self, user_id: str, session_id: str, trial_id: str) -> list[CodePassage]:
        async with self._factory() as db:
            row = await _bound(TrialRepository(db, user_id), trial_id, session_id)
            return excerpts(row.snapshot)

    async def save(
        self, user_id: str, session_id: str, trial_id: str, pleadings: list[CodePleading]
    ) -> None:
        async with self._factory() as db:
            repo = TrialRepository(db, user_id)
            row = await _bound(repo, trial_id, session_id)
            if row.pleadings:
                return
            if not await repo.save_pleadings(row, session_id, pleadings):
                await db.refresh(row)
                if row.session_id != session_id or not row.pleadings:
                    raise AppError("code_trial_closed", "This session can no longer publish.", 409)
            await db.commit()

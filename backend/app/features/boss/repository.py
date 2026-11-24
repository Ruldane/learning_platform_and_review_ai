"""One attempt per program and account, reserved before creating the IDE session."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from app.core.errors import AppError
from app.db.base import new_id
from app.db.models.boss import BossAttempt
from app.db.repository import UserScopedRepository
from app.features.boss.challenge import BRIEF, CHANGE, CHANGE_DELAY, DURATION


class BossRepository(UserScopedRepository[BossAttempt]):
    model = BossAttempt

    async def for_program(self, program_id: str) -> BossAttempt | None:
        stmt = (
            select(BossAttempt)
            .where(BossAttempt.user_id == self.user_id, BossAttempt.program_id == program_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def require(self, program_id: str) -> BossAttempt:
        row = await self.for_program(program_id)
        if row is None:
            raise AppError("boss_not_found", "Start the challenge first.", 404)
        return row

    async def reserve(self, program_id: str, at: datetime) -> tuple[BossAttempt, bool]:
        stmt = (
            insert(BossAttempt)
            .values(
                id=new_id(),
                user_id=self.user_id,
                program_id=program_id,
                ide_session_id="",
                started_at=at,
                change_at=at + CHANGE_DELAY,
                deadline_at=at + DURATION,
                brief=BRIEF,
                change=CHANGE,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "program_id"])
            .returning(BossAttempt.id)
        )
        reserved = (await self.session.execute(stmt)).scalar_one_or_none() is not None
        return await self.require(program_id), reserved

    async def record_grade(
        self, program_id: str, session_id: str, verdict: dict[str, Any], proof: bool
    ) -> bool:
        stmt = (
            update(BossAttempt)
            .where(
                BossAttempt.user_id == self.user_id,
                BossAttempt.program_id == program_id,
                BossAttempt.review_session_id == session_id,
                BossAttempt.verdict.is_(None),
            )
            .values(verdict=verdict, proof_recorded=proof)
            .returning(BossAttempt.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

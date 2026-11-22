"""Parcours du défi, horodaté côté serveur et au nom du compte courant."""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.boss_port import BossGrade
from app.core.caller import Caller
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.boss import BossAttempt
from app.features.boss.challenge import ENTRY, TITLE, starter_files
from app.features.boss.repository import BossRepository
from app.features.boss.schemas import BossAttemptOut, BossClientChange, BossProgramOut, BossState
from app.features.ide.service import IdeService
from app.features.program.service.programs import Loaded, load
from app.features.sessions.service import session_facts

type Clock = Callable[[], datetime]
DEFAULT_CLOCK: Clock = utcnow


def eligible(program: Loaded) -> bool:
    skipped = {module.id for module in program.modules if module.skipped}
    return program.program.status == "validated" and all(
        task.status == "done" or task.module_id in skipped for task in program.tasks
    )


class BossService:
    def __init__(self, db: AsyncSession, user_id: str, clock: Clock) -> None:
        self.db, self.user_id, self.clock = db, user_id, clock
        self.repo = BossRepository(db, user_id)
        self.ide = IdeService(db, user_id, None, Caller("app", "boss"))

    async def _state(self, row: BossAttempt, now: datetime) -> BossState:
        if row.verdict is not None:
            return "graded"
        if row.review_session_id is not None:
            session = await session_facts(self.db, self.user_id, row.review_session_id)
            if session and session.status in {"running", "paused", "waiting_user"}:
                return "reviewing"
            return "review_failed"
        return "expired" if now >= row.deadline_at else "building"

    async def _view(self, row: BossAttempt) -> BossAttemptOut:
        now = self.clock()
        change = (
            BossClientChange(at=row.change_at, requirement=row.change)
            if now >= row.change_at
            else None
        )
        return BossAttemptOut(
            id=row.id,
            ide_session_id=row.ide_session_id,
            state=await self._state(row, now),
            started_at=row.started_at,
            deadline_at=row.deadline_at,
            submitted_at=row.submitted_at,
            server_time=now,
            brief=row.brief,
            client_change=change,
            grade=BossGrade.model_validate(row.verdict) if row.verdict is not None else None,
            proof_recorded=row.proof_recorded,
        )

    async def read(self, program_id: str) -> BossProgramOut:
        program = await load(self.db, self.user_id, program_id)
        row = await self.repo.for_program(program_id)
        return BossProgramOut(
            program_id=program_id,
            title=program.program.title,
            eligible=eligible(program),
            attempt=await self._view(row) if row is not None else None,
        )

    async def start(self, program_id: str) -> BossAttemptOut:
        program = await load(self.db, self.user_id, program_id)
        existing = await self.repo.for_program(program_id)
        if existing is not None:
            return await self._view(existing)
        if not eligible(program):
            raise AppError(
                "boss_locked", "Termine les tâches du programme pour ouvrir le Boss.", 409
            )
        row, reserved = await self.repo.reserve(program_id, self.clock())
        if reserved:
            project = await self.ide.open_session(title=f"Boss · {TITLE}")
            await self.ide.save_files(project.id, starter_files(), entry=ENTRY)
            row.ide_session_id = project.id
        return await self._view(row)

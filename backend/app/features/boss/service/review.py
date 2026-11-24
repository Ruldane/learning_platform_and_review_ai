"""Boss diagnostic and rubric, run by the background session."""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.boss_port import BossDiagnostic, BossGrade, BossRubric, BossSubmission
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.base import utcnow
from app.db.models.boss import BossAttempt
from app.features.boss.challenge import ENTRY, SKILL
from app.features.boss.repository import BossRepository
from app.features.boss.service import diagnostic
from app.features.skills.service import SkillsService
from app.providers.sandbox.base import CodeSandbox

_SAMPLE_CHARS = 12_000


def _sample(files: dict[str, str]) -> dict[str, str]:
    sample = {ENTRY: files[ENTRY][:_SAMPLE_CHARS]}
    budget = _SAMPLE_CHARS - len(sample[ENTRY])
    for name, source in sorted(files.items()):
        if budget and name != ENTRY and name.endswith(".py"):
            sample[name] = source[:budget]
            budget -= len(sample[name])
    return sample


async def _assigned(repo: BossRepository, program_id: str, session_id: str) -> BossAttempt:
    row = await repo.require(program_id)
    if row.review_session_id != session_id or row.submitted_files is None:
        raise AppError("boss_review_stale", "This session no longer matches the submission.", 409)
    return row


class AgentBossReview:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        sandbox: Callable[[], CodeSandbox | None],
    ) -> None:
        self._factory, self._sandbox = factory, sandbox

    async def diagnose(self, user_id: str, program_id: str, session_id: str) -> BossSubmission:
        async with self._factory() as db:
            row = await _assigned(BossRepository(db, user_id), program_id, session_id)
            code = row.submitted_files or {}
            run_id = row.sandbox_run_id
            cached = row.diagnostic
            brief, change = row.brief, row.change
            previous = BossGrade.model_validate(row.verdict) if row.verdict else None
        if cached is None:
            sandbox = self._sandbox()
            if sandbox is None or run_id is None:
                raise AppError("boss_sandbox_unavailable", "The sandbox is unavailable.", 503)
            result = await diagnostic.run(sandbox, diagnostic.job_for(run_id, code))
            await self._save_diagnostic(user_id, program_id, session_id, result)
        else:
            result = BossDiagnostic.model_validate(cached)
        return BossSubmission(
            brief=brief,
            change=change,
            code_sample=_sample(code),
            diagnostic=result,
            previous=previous,
        )

    async def _save_diagnostic(
        self, user_id: str, program_id: str, session_id: str, result: BossDiagnostic
    ) -> None:
        async with self._factory() as db:
            row = await _assigned(BossRepository(db, user_id), program_id, session_id)
            row.diagnostic = result.model_dump()
            await db.commit()

    async def grade(
        self, user_id: str, program_id: str, session_id: str, rubric: BossRubric
    ) -> BossGrade:
        async with self._factory() as db:
            repo = BossRepository(db, user_id)
            row = await _assigned(repo, program_id, session_id)
            if row.verdict is not None:
                return BossGrade.model_validate(row.verdict)
            result = BossDiagnostic.model_validate(row.diagnostic)
            functional = 10 * sum(check.passed for check in result.checks) // len(result.checks)
            total = functional + rubric.readability.score + rubric.maintenance.score
            grade = BossGrade(
                functionality=functional, total=total, rubric=rubric, diagnostic=result
            )
            proof = result.passed and total >= 14
            acquired = await repo.record_grade(program_id, session_id, grade.model_dump(), proof)
            if not acquired:
                current = await _assigned(repo, program_id, session_id)
                if current.verdict is not None:
                    return BossGrade.model_validate(current.verdict)
                raise AppError("boss_review_stale", "The evaluation has changed.", 409)
            if proof:
                item = evidence("ide", row.ide_session_id, "End-of-program Boss passed", utcnow())
                await SkillsService(db, user_id).raise_levels([SKILL], "en_cours", item)
            await db.commit()
            return grade

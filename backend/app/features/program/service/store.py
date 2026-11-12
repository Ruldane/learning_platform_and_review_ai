"""Port du programme (`ProgramStore`, D86) sur la feature `program` : implémentation branchée par
`bootstrap.agent_ports` (D88). Chaque appel ouvre sa propre session de base, courte, et la
commite (D66) ; chaque appel vérifie que l'objectif, les propositions et le programme sont à
l'utilisateur (404 sinon). Les règles sont celles de 4.2 (`check_draft`, `schedule`) : un seul
jeu de règles pour le Stratège et pour les modifications de January.

L'écriture d'une révision et la validation passent sous le verrou du programme (même verrou que
les modifications de January). Journaux : identifiants seulement (SPEC 17.2)."""

import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.plan_schema import PlanDraft
from app.agents.tools.program_port import BudgetView, DraftSaved, ProgramContext
from app.features.learning.service.goals import brief_of, owned_goal
from app.features.learning.service.proposals import proposal_drafts
from app.features.program.repository import ProgramRepository
from app.features.program.service.budget import Budget
from app.features.program.service.drafting import budget_of, known_skills, save_version
from app.features.program.service.planning import (
    PRACTICE_MINUTES,
    QUIZ_MINUTES,
    PlanningImpossible,
    check_draft,
)
from app.features.program.service.programs import load, plan_text, program_not_found
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.validation import (
    commit_validation,
    start_production,
    sync_skills,
)
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)


def _view(budget: Budget) -> BudgetView:
    return BudgetView(
        budget.weekly_minutes, budget.cap_minutes, budget.weekday_minutes, budget.weekend_minutes
    )


class AgentProgramStore:
    def __init__(self, runtime: ProgramRuntime) -> None:
        self._rt = runtime

    async def _run[T](self, work: Callable[[AsyncSession], Awaitable[T]]) -> T:
        async with self._rt.session_factory() as db:
            result = await work(db)
            await db.commit()
        return result

    async def context(
        self, user_id: str, goal_id: str, proposal_ids: Sequence[str], program_id: str | None
    ) -> ProgramContext:
        async def work(db: AsyncSession) -> ProgramContext:
            goal = await owned_goal(db, user_id, goal_id)
            proposals = await proposal_drafts(db, user_id, goal_id, proposal_ids)
            budget = await budget_of(db, user_id, goal.weekly_minutes)
            if budget.cap_minutes < PRACTICE_MINUTES + QUIZ_MINUTES:
                raise PlanningImpossible()  # avant tout appel au modèle (D86 §9)
            current: str | None = None
            if program_id is not None:
                loaded = await load(db, user_id, program_id)
                if loaded.program.goal_id != goal_id:
                    raise program_not_found()
                current = plan_text(loaded)
            settings = await SettingsService(db, user_id).get()
            known = await known_skills(db, user_id)
            return ProgramContext(
                brief_of(goal),
                proposals,
                _view(budget),
                known,
                settings.lesson_language,
                goal.minutes,
                current,
            )

        return await self._run(work)

    async def check_draft(self, user_id: str, goal_id: str, draft: PlanDraft) -> list[str]:
        async def work(db: AsyncSession) -> list[str]:
            goal = await owned_goal(db, user_id, goal_id)
            return check_draft(draft, await budget_of(db, user_id, goal.weekly_minutes))

        return await self._run(work)

    async def _program_of(self, user_id: str, session_id: str) -> str | None:
        async with self._rt.session_factory() as db:
            program = await ProgramRepository(db, user_id).by_session(session_id)
        return program.id if program is not None else None

    async def save_draft(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        draft: PlanDraft,
        *,
        revision: int,
        start_date: date | None,
        reason: str,
    ) -> DraftSaved:
        async def work(db: AsyncSession) -> DraftSaved:
            goal = brief_of(await owned_goal(db, user_id, goal_id))
            return await save_version(
                db,
                user_id,
                session_id,
                goal,
                draft,
                revision=revision,
                start_date=start_date,
                reason=reason,
                today=date.today(),
            )

        program_id = await self._program_of(user_id, session_id)
        if program_id is None:  # première version : aucun autre écrivain possible
            saved = await self._run(work)
        else:
            async with self._rt.program_lock(user_id, program_id):
                saved = await self._run(work)
        logger.info(
            "Version du programme : utilisateur %s, session %s, programme %s, version %d",
            user_id,
            session_id,
            saved.program_id,
            saved.version,
        )
        return saved

    async def validate(self, user_id: str, session_id: str, program_id: str) -> None:
        """Validation sous le verrou, puis reflet des niveaux en mémoire hors du verrou ; rejoué
        (`finalize` après un redémarrage), rattrape un reflet manqué ; lance enfin les leçons
        des semaines 1 et 2 (D91, une seule chaîne par programme)."""
        async with self._rt.program_lock(user_id, program_id):
            async with self._rt.session_factory() as db:
                program = await ProgramRepository(db, user_id).get_fresh(program_id)
                if program is None or program.session_id != session_id:
                    raise program_not_found()
                await owned_goal(db, user_id, program.goal_id)
            sync = await commit_validation(self._rt, user_id, program_id)
        await sync_skills(self._rt, user_id, sync, session_id=session_id)
        await start_production(self._rt, user_id, program_id)

"""Port du Conseil (`CouncilStore`, D84) sur la feature `learning` : implémentation branchée par
`bootstrap.agent_ports`. Chaque appel ouvre sa propre session de base, courte, et la commite
(D66) ; chaque lecture et écriture est filtrée par utilisateur (un objectif d'un autre : 404).

Le choix et le lancement du programme passent sous le verrou de l'objectif (même verrou que la
route `choose`, D87) : un seul `program_builder` par objectif.

Journaux : identifiants seulement (SPEC 17.2)."""

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.runtime.payloads import BoardKind
from app.agents.tools.council_port import (
    Choice,
    FramingQuestion,
    GoalBrief,
    ProposalDraft,
    ProposalRef,
    SavedProposal,
)
from app.features.learning.repository import GoalRepository
from app.features.learning.service import boards, goals, proposals
from app.features.learning.service.choice import write_choice
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import find_active_session

logger = logging.getLogger(__name__)


def program_input(goal_id: str, choice: Choice) -> dict[str, Any]:
    """Entrée de `program_builder` (`ProgramBuilderInput`) ; ids dédoublonnés dans l'ordre."""
    start = choice.start_date.isoformat() if choice.start_date is not None else None
    ids = list(dict.fromkeys(choice.proposal_ids))
    return {"goal_id": goal_id, "proposal_ids": ids, "start_date": start}


class AgentCouncilStore:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        launcher: SessionLauncher,
        learning: LearningRuntime,
    ) -> None:
        self._db = session_factory
        self._launcher = launcher
        self._learning = learning

    async def _run[T](self, work: Callable[[AsyncSession], Awaitable[T]]) -> T:
        async with self._db() as db:
            result = await work(db)
            await db.commit()
        return result

    async def goal(self, user_id: str, goal_id: str) -> GoalBrief:
        async def work(db: AsyncSession) -> GoalBrief:
            return goals.brief_of(await goals.owned_goal(db, user_id, goal_id))

        return await self._run(work)

    async def save_framing(
        self,
        user_id: str,
        goal_id: str,
        questions: Sequence[FramingQuestion],
        answers: Mapping[str, str],
    ) -> None:
        await self._run(lambda db: goals.save_framing(db, user_id, goal_id, questions, answers))

    async def save_board(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        step: int,
        kind: BoardKind,
        title: str,
        mermaid: str,
    ) -> str:
        return await self._run(
            lambda db: boards.save_board(
                db, user_id, session_id, goal_id, step=step, kind=kind, title=title, mermaid=mermaid
            )
        )

    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None:
        await self._run(lambda db: goals.save_minutes(db, user_id, goal_id, text))

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        batch: int,
        proposals: Sequence[ProposalDraft],
    ) -> list[ProposalRef]:
        return await self._run(
            lambda db: _save_batch(db, user_id, session_id, goal_id, batch, proposals)
        )

    async def saved_proposals(
        self, user_id: str, session_id: str, *, batch: int
    ) -> list[SavedProposal]:
        return await self._run(
            lambda db: proposals.saved_proposals(db, user_id, session_id, batch=batch)
        )

    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None:
        await self._run(lambda db: proposals.attach_board(db, user_id, proposal_id, board_id))

    async def record_choice(
        self, user_id: str, session_id: str, goal_id: str, choice: Choice
    ) -> None:
        async with self._learning.goal_lock(user_id, goal_id):
            await self._run(lambda db: write_choice(db, user_id, session_id, goal_id, choice))

    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str:
        """Sous le verrou de l'objectif : programme déjà écrit (sa session) ou session
        `program_builder` ouverte → rendue telle quelle ; sinon lancée. L'objectif passe à
        « chosen »."""
        async with self._learning.goal_lock(user_id, goal_id):
            existing = await self._run(lambda db: _program_session(db, user_id, goal_id))
            if existing is not None:
                return existing
            session_id = await self._launcher.start(
                user_id,
                goals.PROGRAM_GRAPH,
                program_input(goal_id, choice),
                subject_type=goals.SUBJECT,
                subject_id=goal_id,
            )
            await self._run(lambda db: _mark_chosen(db, user_id, goal_id))
        logger.info(
            "Programme lancé : utilisateur %s, objectif %s, session %s",
            user_id,
            goal_id,
            session_id,
        )
        return session_id


async def _save_batch(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    goal_id: str,
    batch: int,
    drafts: Sequence[ProposalDraft],
) -> list[ProposalRef]:
    return await proposals.save_proposals(
        db, user_id, session_id, goal_id, batch=batch, proposals=drafts
    )


async def _program_session(db: AsyncSession, user_id: str, goal_id: str) -> str | None:
    await goals.owned_goal(db, user_id, goal_id)
    program = await GoalRepository(db, user_id).latest_program(goal_id)
    if program is not None and program[1] is not None:
        return program[1]
    return await find_active_session(
        db, user_id, graph=goals.PROGRAM_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )


async def _mark_chosen(db: AsyncSession, user_id: str, goal_id: str) -> None:
    goal = await goals.owned_goal(db, user_id, goal_id)
    if goal.status == "council":
        goal.status = "chosen"
        await db.flush()

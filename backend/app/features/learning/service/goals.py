"""Goals (SPEC 3.1, step 1): creation, which starts the Council (`learning_council`), and
reads. Port writes for the goal (framing, minutes).

Logs: identifiers only, never a goal's text or an answer (SPEC 17.2)."""

import builtins
import logging
from collections.abc import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.council_port import FramingQuestion, GoalBrief
from app.core.errors import AppError
from app.db.models.learning import Goal
from app.features.learning.repository import GoalRepository
from app.features.learning.schemas import GoalCreate, GoalOut, GoalStarted
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import find_active_session, find_latest_session

logger = logging.getLogger(__name__)

COUNCIL_GRAPH = "learning_council"
PROGRAM_GRAPH = "program_builder"
SUBJECT = "goal"


def goal_not_found() -> AppError:
    return AppError("goal_not_found", "Goal not found.", 404)


async def owned_goal(db: AsyncSession, user_id: str, goal_id: str) -> Goal:
    """The user's goal, read fresh; 404 if it does not exist or belongs to someone else."""
    goal = await GoalRepository(db, user_id).get_fresh(goal_id)
    if goal is None:
        raise goal_not_found()
    return goal


async def program_of(db: AsyncSession, user_id: str, goal_id: str) -> tuple[str | None, str | None]:
    """`(program, program_builder session)` of the goal: the latest written program and its
    session, otherwise the latest `program_builder` session started (the Strategist has not
    saved anything yet, or it failed)."""
    program = await GoalRepository(db, user_id).latest_program(goal_id)
    if program is not None and program[1] is not None:
        return program
    session = await find_latest_session(
        db, user_id, graph=PROGRAM_GRAPH, subject_type=SUBJECT, subject_id=goal_id
    )
    return (program[0] if program else None, session)


async def goal_out(db: AsyncSession, user_id: str, goal: Goal) -> GoalOut:
    program_id, program_session_id = await program_of(db, user_id, goal.id)
    weekly = goal.weekly_minutes
    return GoalOut(
        id=goal.id,
        text=goal.text,
        target_role=goal.target_role,
        deadline=goal.deadline,
        weekly_hours=None if weekly is None else weekly // 60,
        status=goal.status,  # type: ignore[arg-type]  # text column, GoalStatus values
        council_session_id=goal.council_session_id,
        program_id=program_id,
        program_session_id=program_session_id,
        created_at=goal.created_at,
    )


async def create_goal(
    db: AsyncSession, learning: LearningRuntime, user_id: str, req: GoalCreate
) -> GoalStarted:
    """Saves the goal then starts its Council (no separate session route, D87). The goal is
    committed BEFORE the start: the `context` node reads it again in its own session. Start
    impossible, whatever the error: the goal is removed (`_discard`), the error propagates."""
    goal = await _add_goal(db, user_id, req, status="council")
    await db.commit()
    try:
        session_id = await learning.launcher.start(
            user_id, COUNCIL_GRAPH, {"goal_id": goal.id}, subject_type=SUBJECT, subject_id=goal.id
        )
    except BaseException:
        await _discard(db, user_id, goal.id)
        raise
    goal.council_session_id = session_id
    await db.commit()  # SQLite write lock released right away: the Council is already writing
    logger.info("Goal created: user %s, goal %s, Council %s", user_id, goal.id, session_id)
    return GoalStarted(goal=await goal_out(db, user_id, goal), session_id=session_id)


async def _add_goal(db: AsyncSession, user_id: str, req: GoalCreate, *, status: str) -> Goal:
    weekly = None if req.weekly_hours is None else req.weekly_hours * 60
    return await GoalRepository(db, user_id).add(
        text=req.text,
        target_role=req.target_role,
        deadline=req.deadline,
        weekly_minutes=weekly,
        status=status,
        framing={},
    )


async def write_goal(db: AsyncSession, user_id: str, req: GoalCreate) -> GoalOut:
    """Direct write (phase 10, D213): the goal alone, without Council, session or model call. It
    is already "chosen": no path to choose, the program is written next
    (`POST /programs/direct`). A Council cannot be restarted on it (`council_not_failed`)."""
    goal = await _add_goal(db, user_id, req, status="chosen")
    await db.commit()
    logger.info("Goal written directly: user %s, goal %s", user_id, goal.id)
    return await goal_out(db, user_id, goal)


async def _discard(db: AsyncSession, user_id: str, goal_id: str) -> None:
    """Removes the goal whose Council could not be started, whatever the error (engine
    unavailable, database, input refused): no orphan goal without a Council. Best effort: a
    failed removal is logged and the original error propagates."""
    try:
        await db.rollback()
        await GoalRepository(db, user_id).delete(goal_id)
        await db.commit()
    except Exception:
        logger.warning("Goal not removed after a failed start: goal %s", goal_id)


async def list_goals(db: AsyncSession, user_id: str) -> builtins.list[GoalOut]:
    goals = await GoalRepository(db, user_id).list_recent()
    return [await goal_out(db, user_id, goal) for goal in goals]


async def get_goal(db: AsyncSession, user_id: str, goal_id: str) -> GoalOut:
    return await goal_out(db, user_id, await owned_goal(db, user_id, goal_id))


async def open_council(db: AsyncSession, user_id: str, goal_id: str) -> str | None:
    """The goal's Council session still open, `None` otherwise."""
    return await find_active_session(
        db, user_id, graph=COUNCIL_GRAPH, subject_type=SUBJECT, subject_id=goal_id
    )


# --- Port writes (`AgentCouncilStore`) --------------------------------------------------


def brief_of(goal: Goal) -> GoalBrief:
    answers = goal.framing.get("answers") if isinstance(goal.framing, dict) else None
    return GoalBrief(
        goal_id=goal.id,
        text=goal.text,
        target_role=goal.target_role,
        deadline=goal.deadline,
        weekly_minutes=goal.weekly_minutes,
        framing=dict(answers) if isinstance(answers, dict) else {},
    )


async def save_framing(
    db: AsyncSession,
    user_id: str,
    goal_id: str,
    questions: Sequence[FramingQuestion],
    answers: Mapping[str, str],
) -> None:
    """Framing questions and answers; overwrites the previous ones (idempotent)."""
    goal = await owned_goal(db, user_id, goal_id)
    goal.framing = {
        "questions": [{"id": q.id, "question": q.question} for q in questions],
        "answers": dict(answers),
    }
    await db.flush()


async def save_minutes(db: AsyncSession, user_id: str, goal_id: str, text: str) -> None:
    goal = await owned_goal(db, user_id, goal_id)
    goal.minutes = text
    await db.flush()


async def mark_planned(db: AsyncSession, user_id: str, goal_id: str) -> None:
    """Program validated (D88): the goal moves to "planned"."""
    goal = await owned_goal(db, user_id, goal_id)
    if goal.status != "planned":
        goal.status = "planned"
        await db.flush()

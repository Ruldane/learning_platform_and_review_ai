"""Starts of a goal's flows and their retries after a failure (D87, D97).

- `launch_program`: starts `program_builder` and moves the goal to "chosen"; called under the
  goal's lock by the port (`start_program`, `finalize` node) and by the `choose` route.
- `retry_program`: the `choose` route restarts the Strategist when the same choice is already
  made, the Council closed, and there is neither a program nor an open `program_builder` session.
- `retry_council`: `POST /goals/{id}/council` restarts a failed Council from the beginning,
  keeping the goal.

Logs: identifiers only (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.council_port import Choice
from app.core.errors import AppError
from app.core.played import inherit_source
from app.db.models.learning import Goal
from app.features.learning.repository import GoalRepository
from app.features.learning.schemas import GoalStarted
from app.features.learning.service import goals
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import find_active_session, find_latest_session, session_facts

logger = logging.getLogger(__name__)

OPEN_STATUSES = ("running", "waiting_user", "paused")
MONDAY = 0


def program_input(goal_id: str, choice: Choice) -> dict[str, Any]:
    """`program_builder` input (`ProgramBuilderInput`); ids deduplicated in order."""
    start = choice.start_date.isoformat() if choice.start_date is not None else None
    ids = list(dict.fromkeys(choice.proposal_ids))
    return {"goal_id": goal_id, "proposal_ids": ids, "start_date": start}


async def program_session(db: AsyncSession, user_id: str, goal_id: str) -> str | None:
    """Session of the latest written program, otherwise the open `program_builder` session,
    otherwise `None` (nothing in progress: a start is allowed)."""
    await goals.owned_goal(db, user_id, goal_id)
    program = await GoalRepository(db, user_id).latest_program(goal_id)
    if program is not None and program[1] is not None:
        return program[1]
    return await find_active_session(
        db, user_id, graph=goals.PROGRAM_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )


async def launch_program(
    factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    user_id: str,
    goal_id: str,
    choice: Choice,
) -> str:
    """Starts `program_builder` then moves the goal to "chosen". The caller holds the goal's
    lock and has checked that no program is in progress (`program_session`)."""
    session_id = await launcher.start(
        user_id,
        goals.PROGRAM_GRAPH,
        program_input(goal_id, choice),
        subject_type=goals.SUBJECT,
        subject_id=goal_id,
    )
    async with factory() as db:
        goal = await goals.owned_goal(db, user_id, goal_id)
        if goal.status == "council":
            goal.status = "chosen"
        await db.commit()
    return session_id


def _coming_monday(value: object) -> date | None:
    """Start date taken from a previous input, if it is still an upcoming Monday."""
    try:
        start = date.fromisoformat(str(value))
    except ValueError:
        return None
    return start if start.weekday() == MONDAY and start >= date.today() else None


async def _previous_start(db: AsyncSession, user_id: str, goal_id: str) -> date | None:
    previous = await find_latest_session(
        db, user_id, graph=goals.PROGRAM_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )
    facts = None if previous is None else await session_facts(db, user_id, previous)
    return None if facts is None else _coming_monday(facts.input.get("start_date"))


async def retry_program(
    learning: LearningRuntime,
    user_id: str,
    goal_id: str,
    council_status: str,
    ids: Sequence[str],
    start: date | None,
    council_session_id: str | None = None,
) -> str | None:
    """Under the goal's lock, the same choice being already written: restarts
    `program_builder` if the Council is closed (`finalize` done or stopped), no Council is open
    for the goal, and there is neither a program nor an open `program_builder` session. Start
    date: `start`, otherwise the previous input's if it is still an upcoming Monday. Returns the
    started session, `None` if nothing is restarted. The Council's source (played client or
    forced provider) is carried over."""
    if council_status in OPEN_STATUSES:
        return None
    async with learning.session_factory() as db:
        if await program_session(db, user_id, goal_id) is not None:
            return None
        if await goals.open_council(db, user_id, goal_id) is not None:
            return None
        start = start or await _previous_start(db, user_id, goal_id)
        council = (
            await session_facts(db, user_id, council_session_id) if council_session_id else None
        )
    action: Literal["choose", "mix"] = "mix" if len(ids) == 2 else "choose"
    choice = Choice(action, tuple(ids), start)
    with inherit_source(
        user_id,
        council.played_by if council else None,
        council.model_provider if council else None,
        has_origin=council is not None,
    ):
        session_id = await launch_program(
            learning.session_factory, learning.launcher, user_id, goal_id, choice
        )
    logger.info("Program restarted: user %s, goal %s, session %s", user_id, goal_id, session_id)
    return session_id


def council_not_failed(status: str | None) -> AppError:
    return AppError(
        "council_not_failed",
        "This goal's Council has not failed: there is nothing to restart.",
        409,
        {"status": status},
    )


def goal_already_chosen() -> AppError:
    return AppError(
        "goal_already_chosen",
        "A program has already been started for this goal: the Council can no longer restart.",
        409,
    )


async def _failed_council_goal(db: AsyncSession, user_id: str, goal_id: str) -> Goal:
    goal = await goals.owned_goal(db, user_id, goal_id)
    latest = await find_latest_session(
        db, user_id, graph=goals.COUNCIL_GRAPH, subject_type=goals.SUBJECT, subject_id=goal_id
    )
    facts = None if latest is None else await session_facts(db, user_id, latest)
    status = None if facts is None else facts.status
    if status != "failed":
        raise council_not_failed(status)
    if goal.status != "council":
        raise goal_already_chosen()
    return goal


async def retry_council(learning: LearningRuntime, user_id: str, goal_id: str) -> GoalStarted:
    """Under the goal's lock: the latest `learning_council` session must be `failed`
    (otherwise 409 `council_not_failed`, with its status) and no program started (409
    `goal_already_chosen`). The Council starts over: framing and minutes cleared, then a new
    session, stored on the goal. The failed Council's batches and boards stay in the database;
    its proposals are no longer returned nor choosable (`latest_batch`)."""
    async with learning.goal_lock(user_id, goal_id):
        async with learning.session_factory() as db:
            goal = await _failed_council_goal(db, user_id, goal_id)
            goal.framing, goal.minutes = {}, None
            await db.commit()  # before the start: the `context` node reads the goal again
        session_id = await learning.launcher.start(
            user_id,
            goals.COUNCIL_GRAPH,
            {"goal_id": goal_id},
            subject_type=goals.SUBJECT,
            subject_id=goal_id,
        )
        async with learning.session_factory() as db:
            goal = await goals.owned_goal(db, user_id, goal_id)
            goal.council_session_id = session_id
            await db.commit()
            out = await goals.goal_out(db, user_id, goal)
    logger.info("Council restarted: user %s, goal %s, Council %s", user_id, goal_id, session_id)
    return GoalStarted(goal=out, session_id=session_id)

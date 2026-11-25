"""Path choice (SPEC 3.1, step 6; breakpoint no. 2, D85, D87).

The route writes the choice then resumes the `choose_path` interrupt; the Council's `finalize`
node rewrites the same choice (`write_choice`, the same write) and alone starts `program_builder`
through the port. The generic resume (`/sessions/{id}/resume`) remains possible: everything goes
through `finalize`, under the goal's lock (`LearningRuntime.goal_lock`), hence a single program.

Reads and writes in short sessions opened under the lock: the request that was waiting for the
lock sees what the previous one committed (double click: same state returned, nothing
restarted)."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.handle import AgentRuntime
from app.agents.tools.council_port import Choice
from app.core.errors import AppError
from app.features.learning.repository import ProposalRepository
from app.features.learning.schemas import ChooseOut, ChooseRequest
from app.features.learning.service.goals import owned_goal
from app.features.learning.service.launching import MONDAY, retry_program
from app.features.learning.service.proposals import latest_batch, proposal_not_found
from app.features.learning.service.runtime import LearningRuntime
from app.features.sessions.service import ResumeRequest, SessionsService, SessionView

logger = logging.getLogger(__name__)

CHOICE_KIND = "choose_path"


def invalid_mix() -> AppError:
    return AppError(
        "invalid_mix", "A mix combines two distinct proposals from the latest batch.", 422
    )


def proposal_outdated() -> AppError:
    return AppError(
        "proposal_outdated",
        "This proposal comes from an earlier batch: choose from the latest one.",
        409,
    )


def council_not_waiting(status: str) -> AppError:
    return AppError(
        "council_not_waiting",
        "The Council is not waiting for a choice right now.",
        409,
        {"status": status},
    )


def check_start_date(start: date | None) -> None:
    """Program start: a Monday, today or later (like `PATCH /programs`); otherwise 422
    `invalid_start_date`, field path only, never the value."""
    if start is not None and (start.weekday() != MONDAY or start < date.today()):
        raise AppError(
            "invalid_start_date",
            "A program starts on a Monday, today or later.",
            422,
            {"fields": ["start_date"]},
        )


async def write_choice(
    db: AsyncSession, user_id: str, session_id: str, goal_id: str, choice: Choice
) -> None:
    """Marks exactly the chosen proposals in their batch (the batch's others no longer are):
    replayed, the same write changes nothing. Proposals of the goal and the session, from a
    single batch, otherwise 404 / 422."""
    await owned_goal(db, user_id, goal_id)
    repo = ProposalRepository(db, user_id)
    batches: set[int] = set()
    for proposal_id in choice.proposal_ids:
        row = await repo.get_fresh(proposal_id)
        if row is None or row.goal_id != goal_id or row.session_id != session_id:
            raise proposal_not_found()
        batches.add(row.batch)
    if len(batches) != 1:
        raise invalid_mix()
    await repo.set_chosen(session_id, batches.pop(), set(choice.proposal_ids))


def _choice_ids(batch_ids: Sequence[str], proposal_id: str, mix_with: str | None) -> list[str]:
    if proposal_id not in batch_ids:
        raise proposal_outdated()
    if mix_with is None:
        return [proposal_id]
    if mix_with == proposal_id or mix_with not in batch_ids:
        raise invalid_mix()
    return [proposal_id, mix_with]


async def _view(
    runtime: AgentRuntime, learning: LearningRuntime, user_id: str, session_id: str
) -> SessionView:
    async with learning.session_factory() as db:
        return await SessionsService(db, user_id, runtime).get(session_id)


async def _write(
    learning: LearningRuntime, user_id: str, session_id: str, goal_id: str, choice: Choice | None
) -> None:
    """Writes the choice (or clears it, `choice=None`) and commits right away: the `finalize`
    node rewrites in its own session."""
    async with learning.session_factory() as db:
        if choice is None:
            batch = await latest_batch(db, user_id, goal_id)
            if batch:
                await ProposalRepository(db, user_id).set_chosen(session_id, batch[0].batch, ())
        else:
            await write_choice(db, user_id, session_id, goal_id, choice)
        await db.commit()


async def _resume(
    runtime: AgentRuntime,
    learning: LearningRuntime,
    user_id: str,
    session_id: str,
    request: ResumeRequest,
) -> SessionView:
    async with learning.session_factory() as db:
        return await SessionsService(db, user_id, runtime).resume(session_id, request)


def _resume_value(choice: Choice) -> dict[str, Any]:
    start = choice.start_date.isoformat() if choice.start_date is not None else None
    return {"action": choice.action, "proposal_ids": list(choice.proposal_ids), "start_date": start}


async def _forget(learning: LearningRuntime, user_id: str, session_id: str, goal_id: str) -> None:
    """Clears the written choice, best effort: a choice left written blocks nothing (a Council
    still waiting is always resumed on the next click), it would only be shown wrongly."""
    try:
        await _write(learning, user_id, session_id, goal_id, None)
    except Exception:
        logger.warning(
            "Choice not cleared after a failed resume: user %s, goal %s",
            user_id,
            goal_id,
        )


async def _write_and_resume(
    runtime: AgentRuntime,
    learning: LearningRuntime,
    user_id: str,
    goal_id: str,
    session_id: str,
    choice: Choice,
    interrupt_id: str,
) -> SessionView:
    """Choice written then interrupt resumed. Failed resume, for whatever reason (question
    already answered, engine stopped, database locked, back end shutting down): choice cleared,
    `finalize` will write the one it receives; an already answered question gives 409
    `council_not_waiting` with the status read again after the failure."""
    await _write(learning, user_id, session_id, goal_id, choice)
    request = ResumeRequest(interrupt_id=interrupt_id, value=_resume_value(choice))
    try:
        return await _resume(runtime, learning, user_id, session_id, request)
    except BaseException as exc:
        await _forget(learning, user_id, session_id, goal_id)
        if isinstance(exc, AppError) and exc.code == "stale_interrupt":
            status = (await _view(runtime, learning, user_id, session_id)).status
            raise council_not_waiting(status) from None
        raise


async def choose(
    runtime: AgentRuntime,
    learning: LearningRuntime,
    db: AsyncSession,
    user_id: str,
    proposal_id: str,
    req: ChooseRequest,
) -> ChooseOut:
    """Under the goal's lock: (1) proposal (and `mix_with`) from the latest batch; (2) Council
    waiting on `choose_path` → choice written then interrupt resumed, **always** (a choice left
    written by a failed resume does not block); (3) Council not waiting: same set already
    chosen → Strategist restarted if it failed without a program (`retry_program`,
    `already_chosen` false), otherwise state returned, `already_chosen` true, nothing changed
    (`start_date` included; double click, generic resume finished); another set: 409
    `council_not_waiting`. `start_date`: an upcoming Monday, otherwise 422
    `invalid_start_date`."""
    check_start_date(req.start_date)
    goal_id = await ProposalRepository(db, user_id).goal_of(proposal_id)
    if goal_id is None:
        raise proposal_not_found()
    async with learning.goal_lock(user_id, goal_id):
        async with learning.session_factory() as fresh:
            batch = await latest_batch(fresh, user_id, goal_id)
        ids = _choice_ids([p.id for p in batch], proposal_id, req.mix_with)
        session_id = batch[0].session_id
        view = await _view(runtime, learning, user_id, session_id)
        pending = view.pending_interrupt
        if view.status != "waiting_user" or pending is None or pending.kind != CHOICE_KIND:
            if {p.id for p in batch if p.chosen} != set(ids):
                raise council_not_waiting(view.status)
            retried = await retry_program(
                learning, user_id, goal_id, view.status, ids, req.start_date, session_id
            )
            return ChooseOut(
                council_session_id=session_id, status=view.status, already_chosen=retried is None
            )
        action: Literal["choose", "mix"] = "mix" if len(ids) == 2 else "choose"
        choice = Choice(action, tuple(ids), req.start_date)
        resumed = await _write_and_resume(
            runtime, learning, user_id, goal_id, session_id, choice, pending.interrupt_id
        )
    logger.info(
        "Path chosen through the route: user %s, goal %s, Council %s, proposals %s",
        user_id,
        goal_id,
        session_id,
        ",".join(ids),
    )
    return ChooseOut(council_session_id=session_id, status=resumed.status)

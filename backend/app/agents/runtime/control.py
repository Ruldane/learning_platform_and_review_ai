"""Session status rules: resume, pause, cancel, messages (SPEC 13.2, D3).

Each status change is a conditional transition in the database
(`SessionRepository.transition`): two concurrent requests (double click on an answer,
pause while the graph is ending) cannot both succeed. The runner then decides what to do with
the task; this module only touches the database.
"""

from collections.abc import Collection
from typing import Any

from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.repositories import SessionRepository
from app.core.errors import AppError
from app.db.models.agents import OPEN_SESSION_STATES, AgentSession

TERMINAL = frozenset({"completed", "failed", "cancelled", "expired"})
OPEN = OPEN_SESSION_STATES  # receives messages, cancellable
PAUSABLE = frozenset({"running", "waiting_user"})

type Factory = async_sessionmaker[AsyncSession]


def _conflict(code: str, message: str, status: str) -> AppError:
    return AppError(code, message, 409, {"status": status})


def stale_interrupt(status: str) -> AppError:
    return _conflict("stale_interrupt", "This question has already been answered.", status)


async def get_owned(db: Factory, user_id: str, session_id: str) -> AgentSession:
    """The session of `user_id`; 404 if it does not exist or belongs to another user."""
    async with db() as session:
        row = await SessionRepository(session, user_id).get(session_id)
    if row is None:
        raise AppError("session_not_found", "Session not found.", 404)
    return row


async def transition(
    db: Factory,
    user_id: str,
    session_id: str,
    *,
    from_: Collection[str],
    to: str,
    **values: Any,
) -> bool:
    async with db() as session:
        done = await SessionRepository(session, user_id).transition(
            session_id, from_=from_, to=to, **values
        )
        await session.commit()
    return done


async def claim_resume(
    db: Factory, user_id: str, session_id: str, interrupt_id: str | None, value: Any
) -> Command[Any] | None:
    """Sets the session to `running` (question cleared) and returns the graph input: the answer
    addressed to the interrupt by its id, or `None` (resume of a pause from the last
    checkpoint). Readable 409 if the question is stale or the session not waiting."""
    row = await get_owned(db, user_id, session_id)
    if (row.pending_interrupt or {}).get("brief") is not None:
        raise AppError("played_step_required", "This step is waiting for the MCP client.", 409)
    if row.status == "waiting_user" and interrupt_id is not None:
        pending = (row.pending_interrupt or {}).get("interrupt_id")
        if interrupt_id != pending or not await transition(
            db,
            user_id,
            session_id,
            from_={"waiting_user"},
            to="running",
            pending_interrupt=None,
            user_delivery={"interrupt_id": interrupt_id, "value": value},
        ):
            raise stale_interrupt(row.status)
        # "Card" form: the answer goes to this interrupt, even if there are others.
        return Command(resume={interrupt_id: value})
    if row.status == "paused" and interrupt_id is None:
        if not await transition(db, user_id, session_id, from_={"paused"}, to="running"):
            raise _not_resumable(row.status)
        return None
    if interrupt_id is not None:
        raise stale_interrupt(row.status)  # already answered, or session no longer waiting
    if row.status == "waiting_user":
        raise _conflict(
            "interrupt_required",
            "This session is waiting for an answer to its question.",
            row.status,
        )
    raise _not_resumable(row.status)


def _not_resumable(status: str) -> AppError:
    return _conflict(
        "session_not_resumable", "This session cannot be resumed in its current state.", status
    )


async def claim_pause(db: Factory, user_id: str, session_id: str) -> bool:
    """`True` if the session just paused, `False` if it already was; 409 if
    it is finished. The pending question is cleared: resuming will ask it again."""
    row = await get_owned(db, user_id, session_id)
    if row.status == "paused":
        return False
    if not await transition(
        db,
        user_id,
        session_id,
        from_=PAUSABLE,
        to="paused",
        pending_interrupt=None,
        user_delivery=None,
    ):
        status = (await get_owned(db, user_id, session_id)).status
        if status == "paused":
            return False
        raise _conflict(
            "session_not_pausable", "This session has ended and cannot be paused.", status
        )
    return True


async def claim_cancel(db: Factory, user_id: str, session_id: str) -> None:
    await get_owned(db, user_id, session_id)  # 404 before 409
    if not await transition(
        db,
        user_id,
        session_id,
        from_=OPEN,
        to="cancelled",
        pending_interrupt=None,
        user_delivery=None,
    ):
        status = (await get_owned(db, user_id, session_id)).status
        raise _conflict("session_not_cancellable", "This session has already ended.", status)


async def check_open(db: Factory, user_id: str, session_id: str) -> None:
    """A finished session no longer receives messages (409)."""
    row = await get_owned(db, user_id, session_id)
    if row.status not in OPEN:
        raise _conflict(
            "session_closed",
            "This session has ended and cannot receive messages.",
            row.status,
        )

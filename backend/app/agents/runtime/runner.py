"""`SessionRunner`: starts, resumes, pauses, cancels the sessions and resumes those that a
server stop interrupted. One asyncio task per active session, always tracked: none is orphaned,
`shutdown` cancels them and waits for them.

The body of a task lives in `execution.py`, the status rules in `control.py`.
"""

import asyncio
import contextlib
import contextvars
import logging
from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.runtime import control
from app.agents.runtime.bus import EventBus
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.creation import PrepareSession, persist_session, validated_input
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.events import SessionEvent, UserCommand
from app.agents.runtime.execution import RunContext, run_session, unknown_graph
from app.agents.runtime.playback import claim_step
from app.agents.runtime.ports import NO_PORTS, AgentPorts
from app.agents.runtime.repositories import SessionRepository, list_sessions_to_recover
from app.agents.runtime.run_settings import RunSettingsSource
from app.core.caller import MCP_IDENTITY
from app.core.errors import AppError
from app.core.launch_quota import LaunchQuota
from app.core.played import PLAY_CONTEXT, run_source
from app.db.models.agents import AgentSession

logger = logging.getLogger(__name__)

STOPPING_CODE = "server_stopping"  # recognised by `SessionLauncher`
ACCOUNT_DELETING_CODE = "account_deleting"
_STOPPING = "The server is shutting down. Try again in a moment."
_DELETING = "Sessions cannot start while the account is being deleted."


@dataclass(eq=False)
class _Gate:
    """Control lock of a session; forgotten once nobody holds it or waits for it."""

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


class SessionRunner:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        bus: EventBus,
        models: ChatModelSource,
        checkpointer: BaseCheckpointSaver[Any],
        prices: Mapping[str, ModelPrice],
        run_settings: RunSettingsSource,
        graphs: Mapping[str, GraphSpec] = GRAPHS,
        ports: AgentPorts = NO_PORTS,
        launch_quota: LaunchQuota | None = None,
    ) -> None:
        self.launch_quota = launch_quota or LaunchQuota()  # cap on MCP launches (M11)
        self._db = session_factory
        self._bus = bus
        self._ctx = RunContext(
            session_factory, bus, models, checkpointer, prices, graphs, run_settings, ports
        )
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._gates: dict[str, _Gate] = {}
        self._stopping = False
        self._deleting: set[str] = set()  # accounts whose "Delete everything" is in progress

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        subject_type: str | None = None,
        subject_id: str | None = None,
        *,
        prepare: PrepareSession | None = None,
    ) -> str:
        """Validates the input, creates the `running` session, launches its task and returns."""
        self._refuse_if_stopping()  # before any write: nothing to resume at startup
        self._refuse_if_deleting(user_id)
        spec = self._ctx.graphs.get(graph)
        if spec is None:
            raise unknown_graph(graph)
        data = validated_input(spec.input_model, input)
        # MCP identity or played client: counts toward the daily cap (M11),
        # given back if nothing starts.
        client, provider = run_source(user_id)
        limited = client is not None or MCP_IDENTITY.get() is not None
        reserved = self.launch_quota.reserve(user_id) if limited else None
        try:
            sid = await persist_session(
                self._db,
                user_id,
                graph,
                data,
                source=(client, provider),
                subject=(subject_type, subject_id),
                prepare=prepare,
            )
        except BaseException:
            if reserved is not None:
                self.launch_quota.release(user_id, reserved)
            raise
        if user_id in self._deleting:  # "Delete everything" started during the insert
            with contextlib.suppress(AppError):  # already cancelled by the deletion
                await control.claim_cancel(self._db, user_id, sid)
            self._refuse_if_deleting(user_id)
        self._launch(user_id, sid, None)
        if (play := PLAY_CONTEXT.get()) and play.user_id == user_id and play.graph == graph:
            play.started.append(sid)
        return sid

    async def resume(
        self, user_id: str, session_id: str, interrupt_id: str | None, value: Any
    ) -> None:
        """Answer to the pending question (`interrupt_id` = that of `pending_interrupt`), or
        resume from a pause (`interrupt_id=None`) on the last checkpoint."""
        async with self._control(session_id):
            self._refuse_if_stopping()  # before `claim_resume`: the question stays pending
            self._refuse_if_deleting(user_id)
            command = await control.claim_resume(self._db, user_id, session_id, interrupt_id, value)
            await self._settle(session_id)  # the task that asked the question finishes publishing
            self._launch(user_id, session_id, command)

    async def submit_step(self, user_id: str, session_id: str, step_id: str, response: str) -> None:
        async with self._control(session_id):
            self._refuse_if_stopping()
            self._refuse_if_deleting(user_id)
            row = await control.get_owned(self._db, user_id, session_id)
            command, problem = await claim_step(self._db, row, step_id, response)
            await self._settle(session_id)
            self._launch(user_id, session_id, command)
            if problem:
                raise AppError("played_output_invalid", "Invalid reply.", 422, {"reason": problem})

    async def recover_on_startup(self) -> list[str]:
        """Restarts the `running` sessions that a stop interrupted (last checkpoint: no
        finished node replays). `waiting_user` and `paused` wait for the user."""
        async with self._db() as db:
            to_recover = await list_sessions_to_recover(db)
        for user_id, session_id in to_recover:
            self._launch(user_id, session_id, None)
        return [session_id for _, session_id in to_recover]

    # --- User actions --------------------------------------------------------------------

    async def post_message(
        self, user_id: str, session_id: str, text: str, command: UserCommand | None = None
    ) -> SessionEvent:
        """Publishes `user.message` (text, debate command); the nodes read it on the next turn
        (`GraphDeps.user_inputs_since`, D4, D82). Under the control lock, like pause and
        cancellation: a message is never written after an accepted cancellation."""
        async with self._control(session_id):
            await control.check_open(self._db, user_id, session_id)
            return await self._bus.publish(
                user_id=user_id,
                session_id=session_id,
                type="user.message",
                payload={"text": text, "command": command},
            )

    async def pause(self, user_id: str, session_id: str) -> AgentSession:
        async with self._control(session_id):
            if await control.claim_pause(self._db, user_id, session_id):
                await self._stop(user_id, session_id)
        return await control.get_owned(self._db, user_id, session_id)

    async def cancel(self, user_id: str, session_id: str) -> AgentSession:
        async with self._control(session_id):
            await control.claim_cancel(self._db, user_id, session_id)
            await self._close_cancelled(user_id, session_id)
        return await control.get_owned(self._db, user_id, session_id)

    async def settle_cancelled(self, user_id: str, session_id: str) -> None:
        """Stops a session whose cancellation was already committed with the business write."""
        async with self._control(session_id):
            await self._close_cancelled(user_id, session_id)

    async def _close_cancelled(self, user_id: str, session_id: str) -> None:
        await self._stop(user_id, session_id)
        await self._bus.close(user_id=user_id, session_id=session_id)

    async def delete_threads(self, session_ids: Iterable[str]) -> None:
        """Erases the resume points (checkpointer threads) of these sessions, pending writes
        included; a missing thread is not an error. The caller cancelled the sessions
        beforehand (no task writes into these threads any more)."""
        for session_id in session_ids:
            await self._ctx.checkpointer.adelete_thread(session_id)

    @asynccontextmanager
    async def refusing_starts(self, user_id: str) -> AsyncIterator[None]:
        """During "Delete everything": no session of this account starts or resumes
        (`start` and `resume` return 409 `account_deleting`), whoever launches it (another
        session, the scheduler, another tab). Lifted on exit, successful or not: an account
        whose deletion failed works again. Specific to the process."""
        self._deleting.add(user_id)
        try:
            yield
        finally:
            self._deleting.discard(user_id)

    async def open_sessions(self, user_id: str) -> list[str]:
        """The open sessions (`running`, `waiting_user`, `paused`) of this account."""
        async with self._db() as db:
            return await SessionRepository(db, user_id).open_ids(control.OPEN)

    # --- Tasks ---------------------------------------------------------------------------

    def is_active(self, session_id: str) -> bool:
        task = self._tasks.get(session_id)
        return task is not None and not task.done()

    async def shutdown(self) -> None:
        """Server shutdown: cancels and waits for all the tasks WITHOUT changing their status
        (the `running` sessions will be resumed at the next startup)."""
        self._stopping = True
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _refuse_if_stopping(self) -> None:
        if self._stopping:
            raise AppError(STOPPING_CODE, _STOPPING, 503)

    def _refuse_if_deleting(self, user_id: str) -> None:
        if user_id in self._deleting:
            raise AppError(ACCOUNT_DELETING_CODE, _DELETING, 409)

    @asynccontextmanager
    async def _control(self, session_id: str) -> AsyncIterator[None]:
        """Holds the session's control lock. No wait before `acquire`: a called action takes
        its place in the queue from its first step."""
        gate = self._gates.setdefault(session_id, _Gate())
        gate.users += 1
        try:
            async with gate.lock:
                yield
        finally:
            gate.users -= 1
            if not gate.users and self._gates.get(session_id) is gate:
                del self._gates[session_id]

    async def _run(self, user_id: str, session_id: str, command: Command[Any] | None) -> None:
        async with self._control(session_id):
            pass  # lets the control actions already queued go first (pause, cancellation)
        await run_session(self._ctx, user_id, session_id, command)

    def _launch(self, user_id: str, session_id: str, command: Command[Any] | None) -> None:
        self._refuse_if_stopping()
        # Blank context: launched from another session's node (lesson chain), the task would
        # otherwise inherit its LangChain configuration, hence its cost tracking and its
        # token cap (each call counted twice, D97 no. 12).
        task = asyncio.create_task(
            self._run(user_id, session_id, command),
            name=f"session:{session_id}",
            context=contextvars.Context(),
        )
        self._tasks[session_id] = task
        task.add_done_callback(partial(self._forget, session_id))

    def _forget(self, session_id: str, task: asyncio.Task[None]) -> None:
        if self._tasks.get(session_id) is task:
            del self._tasks[session_id]
        if not task.cancelled() and task.exception() is not None:
            # Outcome impossible to write (database unavailable): the session stays `running` and
            # will be resumed at the next startup.
            logger.error(
                "Session %s: outcome not written (%s)", session_id, type(task.exception()).__name__
            )

    async def _settle(self, session_id: str) -> None:
        """Waits for the current task to finish, without cancelling it."""
        task = self._tasks.get(session_id)
        if task is not None:
            await asyncio.wait({task})

    async def _stop(self, user_id: str, session_id: str) -> None:
        """Cancels the current task, waits for it to finish, then for the publications still
        in flight of THIS session to be written (N5): the view returned afterwards (`last_seq`)
        counts them all (D56), without waiting for those of other sessions."""
        task = self._tasks.get(session_id)
        if task is not None:
            task.cancel()
            await asyncio.wait({task})
            await self._bus.flush(user_id=user_id, session_id=session_id)

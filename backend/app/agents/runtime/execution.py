"""Execution of a session: compiles the graph, walks `astream`, publishes the events, then
writes the outcome (pending question, end, failure).

- `durability="sync"`: a step's checkpoint is written before the next step; an abrupt stop
  never replays a finished node (Review Focus 1).
- Each outcome is a conditional transition from `running`, written in the SAME transaction as
  its event (`EventBus.publish_with`, D61): status and event exist together or not at all. If
  the session was paused or cancelled in the meantime, nothing is written or published.
- Writing the failure outcome (D61 §4): retries (the guard makes them safe), then a fallback
  to an atomic `failed` (`outcome_not_written`), so as never to leave a `running` session
  without a task in the process. If even the fallback fails (database truly unavailable), the
  session stays `running` and is resumed at the next startup.
- The outcome is written in full even if the task is cancelled at that moment (`_settle`).
- LLM calls cut without an end (cancelled: `node_timeout`, pause, shutdown) are counted in
  estimated tokens at the end of each walk of `astream`, whatever its outcome (`flush_cut`, D117).
- `bus.close` only if the session is in the database in a terminal status (and `cancelled`, by
  the runner); never on `waiting_user` or `paused` (D42), nor on an outcome not written (the
  session stays open: a 1000 would be taken for a final end, D50).
"""

import asyncio
import logging
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.pregel import Pregel
from langgraph.types import Command, StreamMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GraphSpec
from app.agents.runtime.bus import EventBus, Guard
from app.agents.runtime.checkpointer import thread_config
from app.agents.runtime.control import TERMINAL
from app.agents.runtime.costs import CostTracker, ModelPrice
from app.agents.runtime.deps import ChatModelSource, GraphDeps
from app.agents.runtime.playback import models_for, public_question
from app.agents.runtime.ports import NO_PORTS, AgentPorts
from app.agents.runtime.recovery import saved_command
from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.runtime.stream import translate_chunk
from app.core.errors import AppError

logger = logging.getLogger(__name__)

STREAM_MODES: list[StreamMode] = ["custom", "messages", "updates"]
INTERNAL_ERROR = "An unexpected error interrupted the session."
NOT_WRITTEN = {
    "code": "outcome_not_written",
    "message": "The session outcome could not be saved. The session was marked as failed.",
}
# Wait before each new attempt to write the outcome (two retries).
OUTCOME_RETRY_DELAYS_S = (0.05, 0.25)


@dataclass(frozen=True)
class RunContext:
    session_factory: async_sessionmaker[AsyncSession]
    bus: EventBus
    models: ChatModelSource
    checkpointer: BaseCheckpointSaver[Any]
    prices: Mapping[str, ModelPrice]
    graphs: Mapping[str, GraphSpec]
    run_settings: RunSettingsSource
    ports: AgentPorts = NO_PORTS


def unknown_graph(name: str) -> AppError:
    return AppError("unknown_graph", f"Unknown workflow: {name}", 404, {"graph": name})


async def run_session(
    ctx: RunContext, user_id: str, session_id: str, command: Command[Any] | None
) -> None:
    """Body of a session's task. `command`: answer to a question, or `None` (start, resume
    from a pause or after a restart: last checkpoint, failing that the input).

    `CancelledError` is re-raised without writing anything: the status belongs to the caller
    (pause, cancellation) or stays `running` (server shutdown, the session will be resumed at
    startup).
    """
    run = _Run(ctx, user_id, session_id)
    try:
        prepared = await run.prepare(command)
        if prepared is None:
            return  # no longer `running` (pause, cancellation came first): nothing to do or write
        graph, config, graph_input = prepared
        pending = await run.stream(graph, graph_input, config)
        if pending is not None:
            outcome = run.wait_user(pending)
        else:
            outcome = run.complete(await _summary(graph, session_id))
    except asyncio.CancelledError:
        raise
    except AppError as exc:
        outcome = run.fail(exc.code, exc.message)
    except Exception as exc:  # raw message never logged or published (keys, data)
        logger.error(
            "Session %s (user %s): unexpected failure (%s)",
            session_id,
            user_id,
            type(exc).__name__,
        )
        outcome = run.fail("internal_error", INTERNAL_ERROR)
    await _settle(outcome)


async def _settle(outcome: Awaitable[None]) -> None:
    """Writes the outcome all the way even if the task is cancelled meanwhile, then lets the
    cancellation follow its course: a status written without its event never happens."""
    task = asyncio.ensure_future(outcome)
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        await asyncio.wait({task})
        if not task.cancelled() and (error := task.exception()) is not None:
            logger.error("Session outcome not written (%s)", type(error).__name__)
        raise


async def _summary(graph: Pregel[Any, Any, Any, Any], session_id: str) -> str:
    values = (await graph.aget_state(thread_config(session_id))).values
    summary = values.get("summary") if isinstance(values, dict) else None
    return summary if isinstance(summary, str) else ""


class _Run:
    def __init__(self, ctx: RunContext, user_id: str, session_id: str) -> None:
        self.ctx = ctx
        self.user_id = user_id
        self.session_id = session_id
        self.tracker: CostTracker | None = None

    async def prepare(
        self, command: Command[Any] | None
    ) -> tuple[Pregel[Any, Any, Any, Any], RunnableConfig, Any] | None:
        """Compiled graph, configuration and input; `None` if the session is no longer
        `running` (a pause or a cancellation came before the task started)."""
        ctx = self.ctx
        async with ctx.session_factory() as db:
            row = await SessionRepository(db, self.user_id).get(self.session_id)
        if row is None:
            raise AppError("session_not_found", "Session not found.", 404)
        if row.status != "running":
            return None
        settings = await ctx.run_settings.get_run_settings(self.user_id)
        spec = ctx.graphs.get(row.graph)
        if spec is None:
            raise unknown_graph(row.graph)
        deps = GraphDeps(
            self.user_id,
            self.session_id,
            models_for(row, ctx.models),
            ctx.bus,
            settings,
            ctx.session_factory,
            ctx.ports,
        )
        graph = spec.build(deps).compile(checkpointer=ctx.checkpointer)
        tracker = self.tracker = CostTracker(
            user_id=self.user_id,
            session_id=self.session_id,
            graph=row.graph,
            bus=ctx.bus,
            session_factory=ctx.session_factory,
            prices=ctx.prices,
            cap_tokens=settings.session_token_cap,
        )
        config: RunnableConfig = {**thread_config(self.session_id), "callbacks": [tracker]}
        if spec.recursion_limit is not None:
            config["recursion_limit"] = spec.recursion_limit
        graph_input: Any = command
        if command is None:
            graph_input = await saved_command(graph, config, row)
            if await ctx.checkpointer.aget_tuple(config) is None:
                graph_input = row.input  # no checkpoint: (re)start from the input
        return graph, config, graph_input

    async def stream(
        self, graph: Pregel[Any, Any, Any, Any], graph_input: Any, config: RunnableConfig
    ) -> dict[str, Any] | None:
        """Publishes the stream; returns the first question asked (one at a time: the other
        pending interruptions will come back on resume, with the same id)."""
        pending: dict[str, Any] | None = None
        try:
            async for mode, chunk in graph.astream(
                graph_input, config, stream_mode=STREAM_MODES, durability="sync"
            ):
                for event in translate_chunk(mode, chunk):
                    if event.type == "interrupt.requested":
                        pending = pending or event.payload
                        continue
                    await self.publish(event.type, event.payload, event.agent)
        finally:
            await self._flush_cut()
        return pending

    async def _flush_cut(self) -> None:
        """Counts the cut calls, all the way even if the task is cancelled meanwhile."""
        if self.tracker is not None:
            await asyncio.shield(self.tracker.flush_cut())

    async def publish(self, type: Any, payload: dict[str, Any], agent: str | None = None) -> None:
        await self.ctx.bus.publish(
            user_id=self.user_id,
            session_id=self.session_id,
            type=type,
            payload=payload,
            agent=agent,
        )

    def _guard(self, to: str, **values: Any) -> Guard:
        async def guard(db: AsyncSession) -> bool:
            return await SessionRepository(db, self.user_id).transition(
                self.session_id,
                from_={"running"},
                to=to,
                play_delivery=None,
                user_delivery=None,
                **values,
            )

        return guard

    async def _outcome(
        self, to: str, event_type: Any, payload: dict[str, Any], **values: Any
    ) -> bool:
        """Status `to` (from `running`) and event `event_type` committed together (D61); `False`
        if the session is no longer `running` (pause, cancellation): nothing is written or sent."""
        event = await self.ctx.bus.publish_with(
            user_id=self.user_id,
            session_id=self.session_id,
            type=event_type,
            payload=payload,
            guard=self._guard(to, **values),
        )
        return event is not None

    async def wait_user(self, pending: dict[str, Any]) -> None:
        # Question and status together: whoever receives the question can answer it right away.
        await self._issue(
            "waiting_user",
            "interrupt.requested",
            public_question(pending),
            pending_interrupt=pending,
        )

    async def complete(self, summary: str) -> None:
        await self._issue("completed", "run.completed", {"summary": summary}, error=None)

    async def fail(self, code: str, message: str) -> None:
        error = {"code": code, "message": message}
        await self._issue("failed", "run.failed", error, error=error)

    async def _issue(
        self, to: str, event_type: Any, payload: dict[str, Any], **values: Any
    ) -> None:
        """Writes the outcome (retries), failing that a `failed` `outcome_not_written`; raises if
        nothing gets written (the session stays `running`). Then `bus.close` if the session is in
        the database in a terminal status: the subscribers receive the final event and stop."""
        try:
            written = await self._persist(to, event_type, payload, **values)
        except Exception as exc:
            logger.error(
                "Session %s: outcome '%s' not written (%s), falling back to failure",
                self.session_id,
                to,
                type(exc).__name__,
            )
            to = "failed"
            written = await self._persist(to, "run.failed", NOT_WRITTEN, error=NOT_WRITTEN)
        # Refused: pause, cancellation, or an earlier attempt committed despite its error.
        final = to in TERMINAL if written else await self._status() in TERMINAL
        if final:
            await self.ctx.bus.close(user_id=self.user_id, session_id=self.session_id)

    async def _persist(
        self, to: str, event_type: Any, payload: dict[str, Any], **values: Any
    ) -> bool:
        """`_outcome` with retries on error (database busy beyond the wait delay).
        Safe: if an attempt committed despite its error, the guard refuses the next one."""
        for delay in OUTCOME_RETRY_DELAYS_S:
            try:
                return await self._outcome(to, event_type, payload, **values)
            except Exception as exc:
                logger.warning(
                    "Session %s: outcome write failed (%s), retrying",
                    self.session_id,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
        return await self._outcome(to, event_type, payload, **values)

    async def _status(self) -> str | None:
        async with self.ctx.session_factory() as db:
            row = await SessionRepository(db, self.user_id).get(self.session_id)
        return None if row is None else row.status

"""Launching a session outside an HTTP request (D82): a feature port (choice of a graph that
launches the building of the program) or a scheduled task (lessons at D-7).

The launcher exists before the engine and is bound to it afterwards (`main._lifespan`, right
after `agent_runtime`): the composition of the ports can receive it without a cycle (the ports
are given to the engine, the engine to the launcher). Unbound, or server stopping: 503
`engine_unavailable`.
"""

import logging
from typing import Any

from app.agents.runtime.creation import PrepareSession
from app.agents.runtime.runner import STOPPING_CODE, SessionRunner
from app.core.errors import AppError

logger = logging.getLogger(__name__)

ENGINE_UNAVAILABLE = "The agent engine is not ready."


def engine_unavailable() -> AppError:
    return AppError("engine_unavailable", ENGINE_UNAVAILABLE, 503)


class SessionLauncher:
    def __init__(self) -> None:
        self._runner: SessionRunner | None = None

    @property
    def runner(self) -> SessionRunner | None:
        return self._runner

    def bind(self, runner: SessionRunner) -> None:
        self._runner = runner

    def unbind(self) -> None:
        """At shutdown, before the engine's: no session is launched through this path any more."""
        self._runner = None

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        prepare: PrepareSession | None = None,
    ) -> str:
        """Like `SessionRunner.start` (validated input, `running` session, task launched); returns
        the session id. The runner's errors (unknown graph, invalid input) pass through
        as they are, except the server shutdown, returned as an engine unavailable."""
        runner = self._runner
        if runner is None:
            logger.warning("Session not launched (user %s): engine not bound", user_id)
            raise engine_unavailable()
        try:
            return await runner.start(
                user_id, graph, input, subject_type, subject_id, prepare=prepare
            )
        except AppError as exc:
            if exc.code != STOPPING_CODE:
                raise
            logger.warning("Session not launched (user %s): server stopping", user_id)
            raise engine_unavailable() from None

    async def resume(self, user_id: str, session_id: str, interrupt_id: str, value: Any) -> None:
        """Like `SessionRunner.resume`: answer to the pending question, given by a feature's
        route ("Generate the PDF" of a CV review, D130). The runner's errors as they are
        (`stale_interrupt`...), except the server shutdown, returned as an engine
        unavailable."""
        runner = self._runner
        if runner is None:
            logger.warning("Session not resumed (user %s): engine not bound", user_id)
            raise engine_unavailable()
        try:
            await runner.resume(user_id, session_id, interrupt_id, value)
        except AppError as exc:
            if exc.code != STOPPING_CODE:
                raise
            logger.warning("Session not resumed (user %s): server stopping", user_id)
            raise engine_unavailable() from None

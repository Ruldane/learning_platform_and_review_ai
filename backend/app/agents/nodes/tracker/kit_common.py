"""Load, route, save, and announce the seven application kit pieces (D142).

The port saves each piece idempotently by application, kind, and session (SPEC 9.4).
Completed pieces emit a `kit_item` artifact independently. Failed pieces instead record
a reason in `meta.error`. Logs use IDs, counts, and status codes (SPEC 17.2).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.agents.runtime.costs import TokenBudgetExceeded
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.kit_schema import KIT_KINDS, KIT_TITLES, KitKind, KitStatus
from app.core.errors import AppError

TIMED_OUT = "This item timed out. Run the kit again to regenerate it."

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: ApplicationKitState) -> ApplicationKitState: ...


@dataclass
class Piece:
    status: KitStatus
    content: str
    meta: dict[str, Any] = field(default_factory=dict)


def say(agent: str, message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{agent}-{message_id}", "text": text}, agent=agent)


async def guarded(limit_s: float, work: Callable[[], Awaitable[Piece]]) -> Piece:
    """Record a branch failure on errors or timeouts and end the run at the token cap."""
    try:
        async with asyncio.timeout(limit_s):
            return await work()
    except TokenBudgetExceeded:
        raise
    except AppError as exc:
        return Piece("failed", "", {"error": exc.message, "code": exc.code})
    except TimeoutError:
        return Piece("failed", "", {"error": TIMED_OUT, "code": "piece_timeout"})


async def finish(
    deps: GraphDeps, application_id: str, kind: KitKind, piece: Piece, *, agent: str
) -> ApplicationKitState:
    """Save the piece, then announce the artifact or its failure."""
    piece_id = await deps.ports.kit.save_piece(
        deps.user_id, deps.session_id, application_id, kind, piece.status, piece.content, piece.meta
    )
    logger.info(
        "Piece saved: session %s, application %s, piece %s, status %s",
        deps.session_id,
        application_id,
        kind,
        piece.status,
    )
    if piece.status == "failed":
        say(agent, f"{kind}-echec", f"{KIT_TITLES[kind]}: {piece.meta['error']}")
    else:
        artifact = {"artifact_id": piece_id, "kind": "kit_item", "title": KIT_TITLES[kind]}
        emit("artifact.ready", artifact, agent=agent)
    return {"outcomes": {kind: piece.status}}


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: ApplicationKitState) -> ApplicationKitState:
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])
        logger.info(
            "Kit loaded: session %s, application %s, %d pieces kept",
            deps.session_id,
            ctx.application_id,
            len(ctx.keep),
        )
        return {"keep": list(ctx.keep)}

    return load


def route_pieces(state: ApplicationKitState) -> list[str]:
    """Run one branch for each missing piece or close if all pieces are kept."""
    kept = set(state.get("keep", []))
    return [kind for kind in KIT_KINDS if kind not in kept] or ["close"]


def close(state: ApplicationKitState) -> ApplicationKitState:
    """Summarize counts by status for `run.completed`."""
    outcomes = list(state.get("outcomes", {}).values())
    kept = len(state.get("keep", []))
    text = (
        f"Application kit: {len(outcomes) + kept} items. {outcomes.count('ready')} ready, "
        f"{outcomes.count('to_check')} to review, {outcomes.count('failed')} failed"
        + (f", {kept} kept unchanged." if kept else ".")
    )
    say("tracker", "fin", text)
    return {"summary": text}

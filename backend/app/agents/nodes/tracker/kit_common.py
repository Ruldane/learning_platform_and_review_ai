"""Ce que les sept branches du kit de candidature ont en commun (D142) : le nœud `load`,
l'aiguillage vers les pièces non gardées, une pièce rangée puis annoncée, la pièce en échec
qui n'arrête pas les autres, et le nœud `close`.

Une pièce est rangée par le port (`save_piece`, idempotent par fiche, pièce et session, SPEC 9.4)
puis annoncée par `artifact.ready` (`kind = "kit_item"`) dès qu'elle est prête, sans attendre les
autres branches. Une pièce « en échec » (`failed`, motif lisible dans `meta.error`) est rangée mais
pas annoncée comme prête.

Journaux : identifiants, nombres et statuts seulement, jamais une pièce ni l'entreprise (17.2)."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.kit_schema import KIT_KINDS, KitKind, KitStatus
from app.core.errors import AppError

TITLES: dict[KitKind, str] = {
    "cv": "CV ciblé",
    "letter": "Lettre de motivation",
    "linkedin": "Messages LinkedIn",
    "followups": "Relances",
    "form_answers": "Réponses aux questions du formulaire",
    "company_brief": "Dossier de l'entreprise",
    "pitch": "Pitch de présentation",
}
TIMED_OUT = "Cette pièce a pris trop de temps : relance le kit pour la refaire."

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
    """La pièce de `work`, ou une pièce en échec si l'agent échoue (`AppError`, message lisible) ou
    dépasse `limit_s` : une branche en échec n'arrête pas les autres."""
    try:
        async with asyncio.timeout(limit_s):
            return await work()
    except AppError as exc:
        return Piece("failed", "", {"error": exc.message, "code": exc.code})
    except TimeoutError:
        return Piece("failed", "", {"error": TIMED_OUT, "code": "piece_timeout"})


async def finish(
    deps: GraphDeps, application_id: str, kind: KitKind, piece: Piece, *, agent: str
) -> ApplicationKitState:
    """Range la pièce par le port, puis l'annonce (prête ou à vérifier) ou dit son échec."""
    piece_id = await deps.ports.kit.save_piece(
        deps.user_id, deps.session_id, application_id, kind, piece.status, piece.content, piece.meta
    )
    logger.info(
        "Pièce rangée : session %s, fiche %s, pièce %s, statut %s",
        deps.session_id,
        application_id,
        kind,
        piece.status,
    )
    if piece.status == "failed":
        say(agent, f"{kind}-echec", f"{TITLES[kind]} : {piece.meta['error']}")
    else:
        artifact = {"artifact_id": piece_id, "kind": "kit_item", "title": TITLES[kind]}
        emit("artifact.ready", artifact, agent=agent)
    return {"outcomes": {kind: piece.status}}


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: ApplicationKitState) -> ApplicationKitState:
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])
        logger.info(
            "Kit lu : session %s, fiche %s, %d pièce(s) gardée(s)",
            deps.session_id,
            ctx.application_id,
            len(ctx.keep),
        )
        return {"keep": list(ctx.keep)}

    return load


def route_pieces(state: ApplicationKitState) -> list[str]:
    """Une branche par pièce non gardée ; toutes gardées : directement `close`."""
    kept = set(state.get("keep", []))
    return [kind for kind in KIT_KINDS if kind not in kept] or ["close"]


def close(state: ApplicationKitState) -> ApplicationKitState:
    """`run.completed` : le compte des pièces par statut."""
    outcomes = list(state.get("outcomes", {}).values())
    kept = len(state.get("keep", []))
    text = (
        f"Kit de candidature : {len(outcomes) + kept} pièce(s), dont {outcomes.count('ready')} "
        f"prête(s), {outcomes.count('to_check')} à vérifier, {outcomes.count('failed')} en échec"
        + (f", {kept} gardée(s) telle(s) quelle(s)." if kept else ".")
    )
    say("tracker", "fin", text)
    return {"summary": text}

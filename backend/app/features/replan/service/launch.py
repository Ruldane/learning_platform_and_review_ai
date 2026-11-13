"""Routes de la replanification (D106) : lancer une replanification sur un message de January
(`POST /programs/{id}/replan`) et lire l'historique des versions (`GET /programs/{id}/versions`).

Le lancement passe sous le verrou de lancement du programme : programme d'un autre → 404,
brouillon → 409 `program_not_validated`, replanification déjà ouverte → 409 `replan_open`
(`details.session_id`). Aucune ligne n'est écrite avant `launcher.start` : la session elle-même
est la trace (D66, D72). Journaux : identifiants seulement."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.program import PlanVersion
from app.features.program.service.programs import load
from app.features.program.service.replan_json import loads_of
from app.features.program.service.replan_versions import version_history
from app.features.replan.repository import ReviewRepository
from app.features.replan.schemas import (
    PlanVersionOut,
    ReplanRequest,
    ReplanStarted,
    VersionDiffOut,
    VersionMoveOut,
    WeekLoadOut,
)
from app.features.replan.service.context import program_not_validated
from app.features.replan.service.runtime import GRAPH, SUBJECT, ReplanRuntime
from app.features.sessions.service import find_active_session, session_facts

logger = logging.getLogger(__name__)

TERMINAL = frozenset({"completed", "failed", "cancelled"})  # sessions closes (D91)


def replan_open(session_id: str) -> AppError:
    return AppError(
        "replan_open",
        "Une replanification de ce programme est déjà en cours.",
        409,
        {"session_id": session_id},
    )


async def open_replan(db: AsyncSession, user_id: str, program_id: str) -> str | None:
    """La session `replan` encore ouverte sur ce programme, s'il y en a une."""
    return await find_active_session(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=program_id
    )


async def start_replan(
    rt: ReplanRuntime, user_id: str, program_id: str, body: ReplanRequest
) -> ReplanStarted:
    async with rt.launch_lock(user_id, program_id):
        async with rt.session_factory() as db:
            loaded = await load(db, user_id, program_id)
            if loaded.program.status != "validated":
                raise program_not_validated()
            running = await open_replan(db, user_id, program_id)
        if running is not None:
            raise replan_open(running)
        payload: dict[str, Any] = {
            "program_id": program_id,
            "trigger": "message",
            "available_minutes": body.available_minutes,
            "message": body.message,
        }
        sid = await rt.launcher.start(
            user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=program_id
        )
    logger.info(
        "Replanification lancée : utilisateur %s, programme %s, session %s",
        user_id,
        program_id,
        sid,
    )
    return ReplanStarted(session_id=sid)


def _diff(version: PlanVersion) -> VersionDiffOut | None:
    raw: dict[str, Any] | None = version.diff
    if not raw:
        return None
    return VersionDiffOut(
        added=list(raw.get("added", [])),
        removed=list(raw.get("removed", [])),
        moved=[VersionMoveOut(task=m[0], before=m[1], after=m[2]) for m in raw.get("moved", [])],
        weeks_before=int(raw.get("weeks_before", 0)),
        weeks_after=int(raw.get("weeks_after", 0)),
    )


def _out(version: PlanVersion, reviews: dict[str, str], closed: set[str]) -> PlanVersionOut:
    status = (
        "superseded" if version.status == "pending" and version.id in closed else version.status
    )
    return PlanVersionOut(
        version=version.version,
        kind=version.kind,  # type: ignore[arg-type]  # colonne texte, valeurs de PlanKind
        status=status,  # type: ignore[arg-type]  # valeurs de PlanStatus
        reason=version.reason,
        created_at=version.created_at,
        accepted_at=version.accepted_at,
        session_id=version.session_id,
        review=reviews.get(version.review_entry_id or ""),
        diff=_diff(version),
        week_loads=[
            WeekLoadOut(
                rank=w.rank, start_date=w.start_date, before=w.before, after=w.after, cap=w.cap
            )
            for w in loads_of(version)
        ],
    )


async def list_versions(db: AsyncSession, user_id: str, program_id: str) -> list[PlanVersionOut]:
    """L'historique du plan, la plus récente d'abord ; 404 si le programme est à un autre. Une
    proposition `pending` dont la session est close est lue `superseded` (`_waiting`)."""
    versions = await version_history(db, user_id, program_id)
    ids = {v.review_entry_id for v in versions if v.review_entry_id}
    reviews = await ReviewRepository(db, user_id).texts(ids)
    closed = {v.id for v in versions if v.status == "pending"}
    closed -= {v.id for v in versions if v.id in closed and await _waiting(db, user_id, v)}
    return [_out(v, reviews, closed) for v in versions]


async def _waiting(db: AsyncSession, user_id: str, version: PlanVersion) -> bool:
    """Une proposition `pending` n'attend que si sa session est encore ouverte ; sinon (session
    annulée, en échec, finie ou introuvable) elle est lue `superseded`, sans écriture (D91) : la
    proposition suivante, ou rien, la remplace. Ne vaut que pour une proposition `replan` : la
    version `build` d'un brouillon peut encore être acceptée par la validation."""
    if version.kind != "replan":
        return True
    if version.session_id is None:
        return False
    facts = await session_facts(db, user_id, version.session_id)
    return facts is not None and facts.status not in TERMINAL

"""Replanning routes (D106): start a replanning from a message by January
(`POST /programs/{id}/replan`) or from a posting gap (`start_gap_replan`, D123), and read the
version history (`GET /programs/{id}/versions`).

Launching runs under the program's launch lock: someone else's program → 404, draft → 409
`program_not_validated`, replanning already open → 409 `replan_open` (`details.session_id`).
No row is written before `launcher.start`: the session itself is the trace (D66, D72).
Logs: identifiers only."""

import logging
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.study_schema import ReplanReading
from app.core.errors import AppError
from app.db.models.program import PlanVersion
from app.features.program.service.programs import load
from app.features.program.service.replan_json import loads_of
from app.features.program.service.replan_versions import version_history
from app.features.replan.repository import ReviewRepository
from app.features.replan.schemas import (
    PlanVersionOut,
    ReplanStarted,
    VersionDiffOut,
    VersionMoveOut,
    WeekLoadOut,
)
from app.features.replan.schemas import ReplanRequest as ReplanRequest
from app.features.replan.service.context import program_not_validated
from app.features.replan.service.runtime import GRAPH, SUBJECT, ReplanRuntime
from app.features.sessions.service import find_active_session, session_facts

logger = logging.getLogger(__name__)

TERMINAL = frozenset({"completed", "failed", "cancelled", "expired"})  # closed sessions (D91)


def replan_open(session_id: str) -> AppError:
    return AppError(
        "replan_open",
        "A replanning of this program is already in progress.",
        409,
        {"session_id": session_id},
    )


async def open_replan(db: AsyncSession, user_id: str, program_id: str) -> str | None:
    """The `replan` session still open on this program, if there is one."""
    return await find_active_session(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=program_id
    )


async def _start(rt: ReplanRuntime, user_id: str, payload: dict[str, Any]) -> str:
    program_id = str(payload["program_id"])
    async with rt.launch_lock(user_id, program_id):
        async with rt.session_factory() as db:
            loaded = await load(db, user_id, program_id)
            if loaded.program.status != "validated":
                raise program_not_validated()
            running = await open_replan(db, user_id, program_id)
        if running is not None:
            raise replan_open(running)
        sid = await rt.launcher.start(
            user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=program_id
        )
    logger.info(
        "Replanning started (%s): user %s, program %s, session %s",
        payload["trigger"],
        user_id,
        program_id,
        sid,
    )
    return sid


async def start_replan(
    rt: ReplanRuntime, user_id: str, program_id: str, body: ReplanRequest
) -> ReplanStarted:
    payload: dict[str, Any] = {
        "program_id": program_id,
        "trigger": "message",
        "available_minutes": body.available_minutes,
        "message": body.message,
    }
    return ReplanStarted(session_id=await _start(rt, user_id, payload))


async def start_gap_replan(
    rt: ReplanRuntime, user_id: str, program_id: str, skills: Sequence[str]
) -> str:
    """ "Add to schedule" (F8, D123): a replanning with the `gap` trigger, additions only in the
    "Skills from postings" module, validated by January. Same refusals as `start_replan`
    (404, 409 `program_not_validated`, 409 `replan_open`)."""
    payload = {"program_id": program_id, "trigger": "gap", "skills": list(skills)}
    return await _start(rt, user_id, payload)


async def start_reading_replan(
    rt: ReplanRuntime, user_id: str, program_id: str, title: str, url: str
) -> str:
    reading = ReplanReading(title=title, url=url)
    payload = {"program_id": program_id, "trigger": "reading", "reading": reading.model_dump()}
    return await _start(rt, user_id, payload)


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
        kind=version.kind,  # type: ignore[arg-type]  # text column, PlanKind values
        status=status,  # type: ignore[arg-type]  # PlanStatus values
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
    """The plan history, most recent first; 404 if the program belongs to someone else. A
    `pending` proposal whose session is closed is read as `superseded` (`_waiting`)."""
    versions = await version_history(db, user_id, program_id)
    ids = {v.review_entry_id for v in versions if v.review_entry_id}
    reviews = await ReviewRepository(db, user_id).texts(ids)
    closed = {v.id for v in versions if v.status == "pending"}
    closed -= {v.id for v in versions if v.id in closed and await _waiting(db, user_id, v)}
    return [_out(v, reviews, closed) for v in versions]


async def _waiting(db: AsyncSession, user_id: str, version: PlanVersion) -> bool:
    """A `pending` proposal only waits while its session is still open; otherwise (session
    cancelled, failed, finished or missing) it is read as `superseded`, without writing (D91):
    the next proposal, or nothing, replaces it. Only applies to a `replan` proposal: the `build`
    version of a draft can still be accepted by validation."""
    if version.kind != "replan":
        return True
    if version.session_id is None:
        return False
    facts = await session_facts(db, user_id, version.session_id)
    return facts is not None and facts.status not in TERMINAL

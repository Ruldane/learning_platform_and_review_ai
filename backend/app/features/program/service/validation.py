"""Validating a program (SPEC 3.1 step 7, 3.2 stop point no. 3; D7, D6, D86, D88).

`validate_program` (`commit_validation` under the lock, then `sync_skills` outside the lock) is
idempotent: `validated` status, accepted version (a "January's edits" version is written first
if the rows have moved since the Strategist's last version), skills reference list, covered
skills raised to "in progress" (never lowered) and each changed level reflected in the memory's
learned item.

The route resumes the Strategist session waiting for its validation, otherwise validates
inline; everything goes under the program lock. Logs: ids only (SPEC 17.2)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.handle import AgentRuntime
from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.core.errors import AppError
from app.core.skills import evidence
from app.features.learning.service.goals import mark_planned
from app.features.lessons.service.production import start_lessons
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.program.repository import PlanVersionRepository
from app.features.program.schemas import ValidateOut
from app.features.program.service.diff import diff_plans, snapshot
from app.features.program.service.editing import check_weeks
from app.features.program.service.programs import Loaded, load, rows_of
from app.features.program.service.runtime import ProgramRuntime
from app.features.sessions.service import ResumeRequest, SessionsService, SessionView
from app.features.skills.service import SkillLevel, SkillsService

logger = logging.getLogger(__name__)

VALIDATION_KIND = "validate_program"
JANUARY_REASON = "Modifications de January"
OPEN_STATUSES = ("running", "waiting_user", "paused")


class ValidationContext(Protocol):
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]: ...

    @property
    def memory(self) -> MemoryRuntime: ...


def program_busy(status: str) -> AppError:
    return AppError(
        "program_not_waiting",
        "The Strategist is still working on this program. Try again in a moment.",
        409,
        {"status": status},
    )


def _same_plan(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a.get("weeks") == b.get("weeks") and a.get("skipped") == b.get("skipped")


async def _accept(db: AsyncSession, user_id: str, loaded: Loaded, now: datetime) -> int:
    """Accepts the version that describes the current rows (written if they have moved)."""
    versions = PlanVersionRepository(db, user_id)
    latest = await versions.latest(loaded.program.id)
    current = snapshot(rows_of(loaded))
    if latest is None or not _same_plan(latest.snapshot, current):
        previous = latest.snapshot if latest is not None else None
        budget = (previous or {}).get("budget")
        latest = await versions.add(
            program_id=loaded.program.id,
            version=await versions.next_version(loaded.program.id),
            snapshot={**current, "budget": budget} if budget else current,
            diff=diff_plans(previous, current).to_json(),
            reason=JANUARY_REASON,
        )
    await versions.supersede_pending(loaded.program.id, keep=latest.id)
    latest.accepted_at, latest.status = now, "accepted"
    return latest.version


def _catalog(raw: dict[str, Any]) -> tuple[list[SkillDraft], list[EdgeDraft]]:
    skills, edges = [], []
    for item in raw.get("skills", []):
        try:
            skills.append(SkillDraft.model_validate(item))
        except ValidationError:
            continue
    for item in raw.get("edges", []):
        try:
            edges.append(EdgeDraft.model_validate(item))
        except ValidationError:
            continue
    return skills, edges


def _covered(loaded: Loaded) -> list[str]:
    """Skills of the planned modules (skipped modules are already known)."""
    return [str(skill) for m in loaded.modules if not m.skipped for skill in m.skills]


async def _raise_skills(
    db: AsyncSession, user_id: str, loaded: Loaded, now: datetime
) -> list[tuple[str, SkillLevel]]:
    """The Strategist's reference list, then skills of the planned modules to "in progress"."""
    service = SkillsService(db, user_id)
    version = await PlanVersionRepository(db, user_id).latest_with_catalog(loaded.program.id)
    if version is not None:
        await service.upsert_catalog(*_catalog(version.snapshot.get("catalog", {})))
    proof = evidence("program", loaded.program.id, f"Programme {loaded.program.title}", now)
    return await service.raise_levels(_covered(loaded), "in_progress", proof)


@dataclass(frozen=True)
class SkillSync:
    """What remains to be reflected in memory, outside the lock: ALL the skills covered by the
    program, at their current level (the reflection is idempotent)."""

    title: str
    levels: list[tuple[str, SkillLevel]]


async def commit_validation(ctx: ValidationContext, user_id: str, program_id: str) -> SkillSync:
    """Validates the program and commits (idempotent: already validated, nothing changes);
    returns the levels to reflect, the "already validated" branch included. To be called under
    the lock."""
    async with ctx.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        program = loaded.program
        changed: list[tuple[str, SkillLevel]] | None = None
        if program.status != "validated":
            now = datetime.now(UTC)
            program.version = await _accept(db, user_id, loaded, now)
            changed = await _raise_skills(db, user_id, loaded, now)
            program.status, program.validated_at = "validated", now
            await mark_planned(db, user_id, program.goal_id)
        levels = await SkillsService(db, user_id).levels_of(_covered(loaded))
        await db.commit()
    if changed is not None:
        logger.info(
            "Program validated: user %s, program %s, %d level(s) changed",
            user_id,
            program_id,
            len(changed),
        )
    return SkillSync(program.title, levels)


async def sync_skills(
    ctx: ValidationContext, user_id: str, sync: SkillSync, *, session_id: str | None
) -> None:
    """Reflects the levels in the memory's learned items (D6), OUTSIDE the lock (vectorizing a
    created item calls Ollama). Idempotent: a missed reflection (failure, stop) is caught up by
    the next call (replay of `finalize`, second "Validate"). A failure is logged."""
    try:
        await reflect_skill_levels(
            ctx.memory,
            user_id,
            sync.levels,
            author="strategist" if session_id else "user",
            session_id=session_id,
            reason=f'Program "{sync.title}" validated',
        )
    except Exception:
        logger.warning("Learned items not reflected after validation: user %s", user_id)


async def validate_program(
    ctx: ValidationContext, user_id: str, program_id: str, *, session_id: str | None
) -> None:
    """Validates (under the lock if the caller holds it) then reflects the levels in memory."""
    sync = await commit_validation(ctx, user_id, program_id)
    await sync_skills(ctx, user_id, sync, session_id=session_id)


async def _session_view(
    runtime: AgentRuntime, rt: ProgramRuntime, user_id: str, session_id: str | None
) -> SessionView | None:
    if session_id is None:
        return None
    async with rt.session_factory() as db:
        try:
            return await SessionsService(db, user_id, runtime).get(session_id)
        except AppError as exc:
            if exc.code == "session_not_found":
                return None
            raise


async def _resume(
    runtime: AgentRuntime, rt: ProgramRuntime, user_id: str, session_id: str, interrupt_id: str
) -> None:
    request = ResumeRequest(interrupt_id=interrupt_id, value="validate")
    async with rt.session_factory() as db:
        try:
            await SessionsService(db, user_id, runtime).resume(session_id, request)
        except AppError as exc:
            if exc.code == "stale_interrupt":
                raise program_busy("running") from None
            raise


async def _under_lock(
    runtime: AgentRuntime, rt: ProgramRuntime, user_id: str, program_id: str
) -> tuple[ValidateOut, SkillSync | None]:
    async with rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
    program = loaded.program
    done = ValidateOut(program_id=program_id, status="validated", session_id=None)
    if program.status == "validated":
        rt.validating.discard(program_id)
        return done, await commit_validation(rt, user_id, program_id)
    check_weeks(loaded, loaded.weeks)
    view = await _session_view(runtime, rt, user_id, program.session_id)
    pending = view.pending_interrupt if view is not None else None
    waiting = view is not None and view.status == "waiting_user"
    if view is not None and waiting and pending is not None and pending.kind == VALIDATION_KIND:
        await _resume(runtime, rt, user_id, view.id, pending.interrupt_id)
        rt.validating.add(program_id)
        logger.info("Validation reprise : programme %s, session %s", program_id, view.id)
        return ValidateOut(program_id=program_id, status="draft", session_id=view.id), None
    if view is None or view.status != "running":
        rt.validating.discard(program_id)
    if view is not None and view.status in OPEN_STATUSES:
        if program_id in rt.validating:
            return ValidateOut(program_id=program_id, status="draft", session_id=view.id), None
        raise program_busy(view.status)
    return done, await commit_validation(rt, user_id, program_id)


async def request_validation(
    runtime: AgentRuntime, rt: ProgramRuntime, user_id: str, program_id: str
) -> ValidateOut:
    """Under the program lock: already validated → 202 without a session; rules checked on the
    current state (422); Strategist waiting on `validate_program` → resume ("validate");
    validation already resumed and running → same state; Strategist busy (revision) → 409;
    otherwise (draft without an open session) → inline validation. Outside the lock afterwards:
    the levels are reflected in memory (catches up a missed reflection, already validated
    program included)."""
    async with rt.program_lock(user_id, program_id):
        out, sync = await _under_lock(runtime, rt, user_id, program_id)
    if sync is not None:
        await sync_skills(rt, user_id, sync, session_id=None)
        await start_production(rt, user_id, program_id)
    return out


async def start_production(rt: ProgramRuntime, user_id: str, program_id: str) -> None:
    """After the validation, outside any program lock: lessons of weeks 1 and 2 launched in a
    chain (D91, idempotent: a single chain per program). Never an error here: a failure is
    logged and the scheduled task catches up."""
    if rt.lessons is not None:
        await start_lessons(rt.lessons, user_id, program_id)

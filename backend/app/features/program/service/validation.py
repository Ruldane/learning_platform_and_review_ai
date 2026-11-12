"""Validation d'un programme (SPEC 3.1 étape 7, 3.2 point d'arrêt n° 3 ; D7, D6, D86, D88).

`validate_program` est idempotente : statut `validated`, version acceptée (une version
« Modifications de January » est écrite d'abord si les lignes ont bougé depuis la dernière
version du Stratège), référentiel de compétences, compétences couvertes montées à « en cours »
(jamais baissées) et chaque niveau changé reflété dans l'acquis de la mémoire.

La route reprend la session du Stratège qui attend sa validation, sinon valide en ligne ; tout
passe sous le verrou du programme. Journaux : identifiants seulement (SPEC 17.2)."""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.handle import AgentRuntime
from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.core.errors import AppError
from app.features.learning.service.goals import mark_planned
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.skill_levels import reflect_skill_level
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
        "Le Stratège travaille encore sur ce programme : réessaie dans un instant.",
        409,
        {"status": status},
    )


def _same_plan(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a.get("weeks") == b.get("weeks") and a.get("skipped") == b.get("skipped")


async def _accept(db: AsyncSession, user_id: str, loaded: Loaded, now: datetime) -> int:
    """Accepte la version qui décrit les lignes actuelles (écrite si elles ont bougé)."""
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
    latest.accepted_at = now
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


async def _raise_skills(
    db: AsyncSession, user_id: str, loaded: Loaded
) -> list[tuple[str, SkillLevel]]:
    """Référentiel du Stratège, puis compétences des modules planifiés à « en cours »."""
    service = SkillsService(db, user_id)
    version = await PlanVersionRepository(db, user_id).latest_with_catalog(loaded.program.id)
    if version is not None:
        await service.upsert_catalog(*_catalog(version.snapshot.get("catalog", {})))
    covered = [str(s) for m in loaded.modules if not m.skipped for s in m.skills]
    return await service.raise_levels(covered, "en_cours", f"Programme {loaded.program.title}")


async def _reflect(
    ctx: ValidationContext,
    user_id: str,
    changed: list[tuple[str, SkillLevel]],
    title: str,
    session_id: str | None,
) -> None:
    """Chaque niveau changé reflété dans l'acquis de la mémoire, au mieux : une panne laisse la
    validation faite (journalisée, identifiants seulement)."""
    author = "strategist" if session_id else "user"
    for name, level in changed:
        try:
            await reflect_skill_level(
                ctx.memory,
                user_id,
                title=name,
                level=level,
                author=author,
                session_id=session_id,
                reason=f"Programme « {title} » validé",
            )
        except Exception:
            logger.warning("Acquis non reflété après validation : utilisateur %s", user_id)


async def validate_program(
    ctx: ValidationContext, user_id: str, program_id: str, *, session_id: str | None
) -> None:
    """Valide le programme (idempotent : déjà validé, rien ne change). À appeler sous le verrou
    du programme."""
    async with ctx.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        program = loaded.program
        if program.status == "validated":
            return
        now = datetime.now(UTC)
        program.version = await _accept(db, user_id, loaded, now)
        changed = await _raise_skills(db, user_id, loaded)
        program.status, program.validated_at = "validated", now
        await mark_planned(db, user_id, program.goal_id)
        await db.commit()
        title = program.title
    await _reflect(ctx, user_id, changed, title, session_id)
    logger.info(
        "Programme validé : utilisateur %s, programme %s, %d niveau(x) changé(s)",
        user_id,
        program_id,
        len(changed),
    )


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


async def request_validation(
    runtime: AgentRuntime, rt: ProgramRuntime, user_id: str, program_id: str
) -> ValidateOut:
    """Sous le verrou du programme : déjà validé → 202 sans session ; règles vérifiées sur l'état
    courant (422) ; Stratège en attente sur `validate_program` → reprise (« validate ») ;
    validation déjà reprise et en cours → même état ; Stratège occupé (révision) → 409 ;
    sinon (brouillon sans session ouverte) → validation en ligne."""
    async with rt.program_lock(user_id, program_id):
        async with rt.session_factory() as db:
            loaded = await load(db, user_id, program_id)
        program = loaded.program
        if program.status == "validated":
            rt.validating.discard(program_id)
            return ValidateOut(program_id=program_id, status="validated", session_id=None)
        check_weeks(loaded, loaded.weeks)
        view = await _session_view(runtime, rt, user_id, program.session_id)
        pending = view.pending_interrupt if view is not None else None
        waiting = view is not None and view.status == "waiting_user"
        if view is not None and waiting and pending is not None and pending.kind == VALIDATION_KIND:
            await _resume(runtime, rt, user_id, view.id, pending.interrupt_id)
            rt.validating.add(program_id)
            logger.info("Validation reprise : programme %s, session %s", program_id, view.id)
            return ValidateOut(program_id=program_id, status="draft", session_id=view.id)
        if view is not None and view.status in OPEN_STATUSES:
            if program_id in rt.validating and view.status == "running":
                return ValidateOut(program_id=program_id, status="draft", session_id=view.id)
            raise program_busy(view.status)
        await validate_program(rt, user_id, program_id, session_id=None)
    return ValidateOut(program_id=program_id, status="validated", session_id=None)

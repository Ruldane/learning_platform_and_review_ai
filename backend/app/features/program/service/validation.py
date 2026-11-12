"""Validation d'un programme (SPEC 3.1 étape 7, 3.2 point d'arrêt n° 3 ; D7, D6, D86, D88).

`validate_program` (`commit_validation` sous le verrou, puis `sync_skills` hors du verrou)
est idempotente : statut `validated`, version acceptée (une version
« Modifications de January » est écrite d'abord si les lignes ont bougé depuis la dernière
version du Stratège), référentiel de compétences, compétences couvertes montées à « en cours »
(jamais baissées) et chaque niveau changé reflété dans l'acquis de la mémoire.

La route reprend la session du Stratège qui attend sa validation, sinon valide en ligne ; tout
passe sous le verrou du programme. Journaux : identifiants seulement (SPEC 17.2)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.handle import AgentRuntime
from app.agents.tools.plan_schema import EdgeDraft, SkillDraft
from app.core.errors import AppError
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


def _covered(loaded: Loaded) -> list[str]:
    """Compétences des modules planifiés (les modules sautés sont déjà acquis)."""
    return [str(skill) for m in loaded.modules if not m.skipped for skill in m.skills]


async def _raise_skills(
    db: AsyncSession, user_id: str, loaded: Loaded
) -> list[tuple[str, SkillLevel]]:
    """Référentiel du Stratège, puis compétences des modules planifiés à « en cours »."""
    service = SkillsService(db, user_id)
    version = await PlanVersionRepository(db, user_id).latest_with_catalog(loaded.program.id)
    if version is not None:
        await service.upsert_catalog(*_catalog(version.snapshot.get("catalog", {})))
    evidence = f"Programme {loaded.program.title}"
    return await service.raise_levels(_covered(loaded), "en_cours", evidence)


@dataclass(frozen=True)
class SkillSync:
    """Ce qu'il reste à refléter dans la mémoire, hors du verrou : TOUTES les compétences
    couvertes par le programme, à leur niveau actuel (le reflet est idempotent)."""

    title: str
    levels: list[tuple[str, SkillLevel]]


async def commit_validation(ctx: ValidationContext, user_id: str, program_id: str) -> SkillSync:
    """Valide le programme et commite (idempotent : déjà validé, rien ne change) ; rend les
    niveaux à refléter, branche « déjà validé » comprise. À appeler sous le verrou."""
    async with ctx.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        program = loaded.program
        changed: list[tuple[str, SkillLevel]] | None = None
        if program.status != "validated":
            now = datetime.now(UTC)
            program.version = await _accept(db, user_id, loaded, now)
            changed = await _raise_skills(db, user_id, loaded)
            program.status, program.validated_at = "validated", now
            await mark_planned(db, user_id, program.goal_id)
        levels = await SkillsService(db, user_id).levels_of(_covered(loaded))
        await db.commit()
    if changed is not None:
        logger.info(
            "Programme validé : utilisateur %s, programme %s, %d niveau(x) changé(s)",
            user_id,
            program_id,
            len(changed),
        )
    return SkillSync(program.title, levels)


async def sync_skills(
    ctx: ValidationContext, user_id: str, sync: SkillSync, *, session_id: str | None
) -> None:
    """Reflète les niveaux dans les acquis de la mémoire (D6), HORS du verrou (la vectorisation
    d'un acquis créé appelle Ollama). Idempotent : un reflet manqué (panne, arrêt) est rattrapé
    par l'appel suivant (rejeu de `finalize`, second « Valider »). Une panne est journalisée."""
    try:
        await reflect_skill_levels(
            ctx.memory,
            user_id,
            sync.levels,
            author="strategist" if session_id else "user",
            session_id=session_id,
            reason=f"Programme « {sync.title} » validé",
        )
    except Exception:
        logger.warning("Acquis non reflétés après validation : utilisateur %s", user_id)


async def validate_program(
    ctx: ValidationContext, user_id: str, program_id: str, *, session_id: str | None
) -> None:
    """Valide (sous le verrou si l'appelant le tient) puis reflète les niveaux en mémoire."""
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
    """Sous le verrou du programme : déjà validé → 202 sans session ; règles vérifiées sur l'état
    courant (422) ; Stratège en attente sur `validate_program` → reprise (« validate ») ;
    validation déjà reprise et en cours → même état ; Stratège occupé (révision) → 409 ;
    sinon (brouillon sans session ouverte) → validation en ligne. Hors du verrou ensuite : les
    niveaux sont reflétés dans la mémoire (rattrape un reflet manqué, programme déjà validé
    compris)."""
    async with rt.program_lock(user_id, program_id):
        out, sync = await _under_lock(runtime, rt, user_id, program_id)
    if sync is not None:
        await sync_skills(rt, user_id, sync, session_id=None)
        await start_production(rt, user_id, program_id)
    return out


async def start_production(rt: ProgramRuntime, user_id: str, program_id: str) -> None:
    """Après la validation, hors de tout verrou du programme : leçons des semaines 1 et 2
    lancées en chaîne (D91, idempotent : une seule chaîne par programme). Jamais d'erreur ici :
    une panne est journalisée et la tâche planifiée rattrape."""
    if rt.lessons is not None:
        await start_lessons(rt.lessons, user_id, program_id)

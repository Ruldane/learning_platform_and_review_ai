"""Exécutions et vérifications dans le bac à sable (P5 à P7). Une seule à la fois par
utilisatrice ; la sortie se lit par décalage d'octets ; la fin (statut, sortie complète, signature
d'erreur) est figée à la première lecture qui la voit. Un code d'utilisatrice ne tourne jamais
ici : seul le bac l'exécute. La sortie n'est jamais journalisée."""

import logging
from typing import Any, cast

from app.db.base import utcnow
from app.db.models.ide import IdeRun, IdeSession
from app.features.ide.repository import ExerciseRepository, RunRepository
from app.features.ide.schemas import RunProgress, RunStatus
from app.features.ide.service import sessions
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import (
    entry_missing,
    run_in_progress,
    run_not_found,
    run_refused,
    sandbox_unavailable,
)
from app.features.ide.service.ghost import record_finished_check
from app.features.ide.service.signature import error_signature
from app.features.skills.service import SkillsService
from app.providers.sandbox.base import (
    MAX_TIMEOUT_S,
    CodeSandbox,
    SandboxJob,
    SandboxKind,
    SandboxProgress,
    UnknownRun,
)

logger = logging.getLogger(__name__)

JOB_TIMEOUT_S = 10  # durée réelle demandée au bac (il plafonne à 15)
PROOF_LABEL = "Exercice réussi : "
RECENT_RUNS = 20


def _sandbox(ctx: IdeContext) -> CodeSandbox:
    if ctx.sandbox is None:
        raise sandbox_unavailable()
    return ctx.sandbox


async def _poll(ctx: IdeContext, run_id: str, offset: int) -> SandboxProgress | None:
    """Ce que le bac rend ; `None` s'il ne connaît pas le travail (nettoyé, jamais déposé)."""
    try:
        return await _sandbox(ctx).poll(run_id, offset)
    except UnknownRun:
        return None
    except OSError:
        raise sandbox_unavailable() from None


def _clean(text: str) -> str:
    """La sortie du code est hostile : le NUL est remplacé par `?` (un octet comme lui, pour que
    les décalages du bac restent valables) ; le front l'affiche comme du texte."""
    return text.replace("\x00", "?")


def _chunk(output: str, after: int) -> tuple[str, int]:
    """La sortie à partir de l'octet `after` (UTF-8), et le décalage suivant."""
    data = output.encode()
    return data[after:].decode(errors="ignore"), len(data)


async def _record_pass(ctx: IdeContext, session: IdeSession) -> None:
    """Première vérification réussie : la séance est réussie, et la compétence de l'exercice (son
    sujet, sinon son titre) gagne une preuve « ide », jamais au-delà de « en cours »."""
    if session.passed_at is None:
        session.passed_at = utcnow()
    names: list[str] = []
    if session.exercise_id is not None:  # supprimé depuis : la séance garde son titre
        exercise = await ExerciseRepository(ctx.db, ctx.user_id).get(session.exercise_id)
        if exercise is not None:
            names = [name for name in (exercise.topic, exercise.title) if name]
    skills = SkillsService(ctx.db, ctx.user_id)
    for name in [*names, session.title]:
        skill_id = await skills.skill_id_for(name)
        if skill_id is not None:
            await skills.add_proof(skill_id, "ide", f"{PROOF_LABEL}{session.title}", session.id)
            return


async def _freeze(ctx: IdeContext, run: IdeRun, progress: SandboxProgress | None) -> None:
    """Fige la fin d'une exécution : statut, code, durée, sortie complète, signature d'erreur."""
    session = await sessions.get(ctx, run.session_id)
    if progress is None or progress.result is None:
        run.status = "error"
    else:
        result = progress.result
        run.status = result.status
        run.exit_code = result.exit_code
        run.duration_ms = result.duration_ms
        run.truncated = result.truncated
        run.output = _clean(progress.output)
        run.error_signature = error_signature(run.output, set(session.files))
    await ctx.db.flush()
    logger.info("Exécution %s terminée : %s", run.id, run.status)
    # Seule une vérification de January valide l'exercice : celle de Claude ne compte pas.
    if run.kind == "check" and run.status == "done" and run.origin == "app":
        if run.exit_code == 0:
            await _record_pass(ctx, session)
            await ctx.db.flush()
        if run.exit_code is not None and session.exercise_id is not None:
            await record_finished_check(ctx.db, run)


async def _settle(ctx: IdeContext, run: IdeRun) -> bool:
    """Interroge le bac sur une exécution en cours ; la fige si elle est finie. Vrai si finie."""
    progress = await _poll(ctx, run.id, 0)
    if progress is not None and progress.result is None:
        return False
    await _freeze(ctx, run, progress)
    return True


async def start(
    ctx: IdeContext,
    session_id: str,
    kind: SandboxKind,
    entry: str | None,
    *,
    source: str | None = None,
    notebook_cell: dict[str, Any] | None = None,
) -> IdeRun:
    session = await sessions.get(ctx, session_id)
    sandbox = _sandbox(ctx)
    repo = RunRepository(ctx.db, ctx.user_id)
    for running in await repo.running():
        if not await _settle(ctx, running):
            raise run_in_progress(running.id)
    wanted = entry or session.entry
    if wanted not in session.files:
        raise entry_missing()
    run = await repo.add(
        session_id=session.id,
        kind=kind,
        entry=wanted,
        requested_by=ctx.caller.label,
        origin=ctx.caller.kind,
        notebook_cell=notebook_cell,
    )
    job = SandboxJob(
        run_id=run.id,
        files={str(path): str(text) for path, text in session.files.items()},
        entry=wanted,
        kind=kind,
        timeout_s=MAX_TIMEOUT_S if kind == "terminal" else JOB_TIMEOUT_S,
        source=source,
        model_user=ctx.user_id if ctx.caller.kind == "app" and kind != "check" else None,
    )
    try:
        await sandbox.submit(job)
    except ValueError:
        raise run_refused() from None
    except OSError:
        raise sandbox_unavailable() from None
    return run


async def progress(
    ctx: IdeContext, run_id: str, after: int, *, kind: SandboxKind | None = None
) -> RunProgress:
    """La sortie depuis l'octet `after`. Fin vue = tout figé (sortie complète, signature)."""
    run = await RunRepository(ctx.db, ctx.user_id).get_fresh(run_id)
    allowed = ("run", "check") if kind is None else (kind,)
    if run is None or run.kind not in allowed:
        raise run_not_found()
    if run.status == "running":
        live = await _poll(ctx, run.id, after)
        if live is not None and live.result is None:
            return RunProgress(
                id=run.id,
                status="running",
                output=_clean(live.output),
                next_offset=live.next_offset,
                exit_code=None,
                duration_ms=None,
                truncated=False,
            )
        await _settle_with(ctx, run, live)
    text, end = _chunk(run.output, after)
    return RunProgress(
        id=run.id,
        status=cast(RunStatus, run.status),
        output=text,
        next_offset=end,
        exit_code=run.exit_code,
        duration_ms=run.duration_ms,
        truncated=run.truncated,
    )


async def _settle_with(ctx: IdeContext, run: IdeRun, live: SandboxProgress | None) -> None:
    """Fige une exécution dont la fin vient d'être vue : relit la sortie complète (le journal est
    complet dès que la fin est visible)."""
    full = await _poll(ctx, run.id, 0) if live is not None else None
    await _freeze(ctx, run, full)


async def list_for(ctx: IdeContext, session_id: str) -> list[IdeRun]:
    """Les `RECENT_RUNS` dernières exécutions de la séance (la page les relit toutes les 3 s)."""
    session = await sessions.get(ctx, session_id)
    return await RunRepository(ctx.db, ctx.user_id).recent_of_session(session.id, RECENT_RUNS)

"""Fin et abandon d'une session guidée (`PATCH`, SPEC 14.2 ; D103 n° 2, 3), sous le verrou de
l'utilisatrice. Une session déjà terminée ou abandonnée est rendue telle quelle (idempotent).

« Terminer » : le minuteur du front (`worked_minutes`, absent : 0) est gardé, borné par la durée
réelle depuis le départ (arrondie à la minute supérieure) et jamais en dessous du temps déjà
gardé (un second « Terminer » sans minuteur ne l'efface pas), PUIS la question en attente reçoit
`{"action": "finish"}` quel que soit son genre (`tutor_question` ou `finish_session`) : le Tuteur
fait son bilan et range la fin par le port (`finish.py`). Fin déjà demandée (temps gardé, Tuteur
en train de conclure) : état rendu ; temps gardé mais question encore en attente (arrêt du back
avant la reprise) : reprise. Tuteur en train d'écrire (aucune question en attente) : 409
`study_not_waiting`, rien n'est gardé. Session d'agents terminée en route (échec, annulation) :
la route range elle-même la fin, sans résultat de questions, pour que le temps compte.

« Abandonner » : la session passe à `cancelled` (rien d'autre : ni temps, ni tâche, ni fiche),
puis sa session d'agents est annulée."""

import logging
import math
from datetime import datetime

from app.agents.runtime.handle import AgentRuntime
from app.core.errors import AppError
from app.db.models.study import StudySession
from app.features.sessions.service import ResumeRequest, SessionsService, SessionView
from app.features.study.repository import StudyRepository
from app.features.study.schemas import StudySessionOut, StudyUpdate
from app.features.study.service.finish import NO_OUTCOME, finish_study
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.view import is_dead, read_row, session_out

logger = logging.getLogger(__name__)

FINISH = {"action": "finish"}


def study_not_waiting(status: str) -> AppError:
    return AppError(
        "study_not_waiting",
        "Le tuteur écrit encore : tu pourras terminer dès qu'il t'aura posé sa question.",
        409,
        {"status": status},
    )


def clamped_minutes(worked: int | None, started: datetime, now: datetime) -> int:
    """`min(minuteur, durée réelle arrondie à la minute supérieure)`, jamais négatif."""
    elapsed = max(0.0, (now - started).total_seconds())
    return max(0, min(worked or 0, math.ceil(elapsed / 60)))


async def _keep_minutes(
    rt: StudyRuntime, user_id: str, row: StudySession, worked: int | None
) -> None:
    # Absent n'efface jamais le temps déjà gardé (un second « Terminer » sans minuteur).
    minutes = max(row.worked_minutes or 0, clamped_minutes(worked, row.created_at, rt.now()))
    async with rt.session_factory() as db:
        await StudyRepository(db, user_id).close_open(row.id, worked_minutes=minutes)
        await db.commit()


async def _forget_minutes(rt: StudyRuntime, user_id: str, row: StudySession) -> None:
    """La reprise a échoué : le temps redevient celui d'avant CE clic (un temps gardé par un
    « Terminer » précédent n'est jamais effacé ; revue finale de la phase 5, S-m5)."""
    async with rt.session_factory() as db:
        await StudyRepository(db, user_id).close_open(row.id, worked_minutes=row.worked_minutes)
        await db.commit()


async def _agent_view(
    runtime: AgentRuntime, rt: StudyRuntime, user_id: str, session_id: str
) -> SessionView:
    async with rt.session_factory() as db:
        return await SessionsService(db, user_id, runtime).get(session_id)


async def _resume(
    runtime: AgentRuntime, rt: StudyRuntime, user_id: str, session_id: str, interrupt_id: str
) -> None:
    request = ResumeRequest(interrupt_id=interrupt_id, value=FINISH)
    async with rt.session_factory() as db:
        await SessionsService(db, user_id, runtime).resume(session_id, request)


async def _finish(
    runtime: AgentRuntime,
    rt: StudyRuntime,
    user_id: str,
    row: StudySession,
    status: str | None,
    worked: int | None,
) -> None:
    if row.session_id is None or is_dead(row, status):
        await _keep_minutes(rt, user_id, row, worked)
        await finish_study(rt, user_id, None, row.id, NO_OUTCOME)
        logger.info("Fin rangée par la route (Tuteur arrêté) : étude %s", row.id)
        return
    view = await _agent_view(runtime, rt, user_id, row.session_id)
    pending = view.pending_interrupt
    if view.status != "waiting_user" or pending is None:
        if row.worked_minutes is not None:
            return  # fin déjà demandée : le Tuteur conclut
        raise study_not_waiting(view.status)
    # Encore en attente (temps gardé puis arrêt du back avant la reprise) : on reprend.
    await _keep_minutes(rt, user_id, row, worked)
    try:
        await _resume(runtime, rt, user_id, row.session_id, pending.interrupt_id)
    except BaseException as exc:
        await _forget_minutes(rt, user_id, row)
        if isinstance(exc, AppError) and exc.code == "stale_interrupt":
            raise study_not_waiting(
                (await _agent_view(runtime, rt, user_id, row.session_id)).status
            ) from None
        raise
    logger.info("Fin demandée : étude %s, session %s", row.id, row.session_id)


async def _cancel(runtime: AgentRuntime, rt: StudyRuntime, user_id: str, row: StudySession) -> None:
    async with rt.session_factory() as db:
        closed = await StudyRepository(db, user_id).close_open(
            row.id, status="cancelled", ended_at=rt.now()
        )
        await db.commit()
    if not closed or row.session_id is None:
        return
    try:
        async with rt.session_factory() as db:
            await SessionsService(db, user_id, runtime).cancel(row.session_id)
    except AppError as exc:  # déjà terminée ou introuvable : rien à arrêter
        if exc.code not in ("session_not_cancellable", "session_not_found"):
            raise
    logger.info("Session d'étude abandonnée : étude %s", row.id)


async def update_study(
    runtime: AgentRuntime, rt: StudyRuntime, user_id: str, study_id: str, body: StudyUpdate
) -> StudySessionOut:
    """« Terminer » ou « Abandonner » (voir le module) ; 404 pour la session d'une autre."""
    async with rt.study_lock(user_id):
        async with rt.session_factory() as db:
            row, status = await read_row(db, user_id, study_id)
        if row.status == "open" and body.action == "cancel":
            await _cancel(runtime, rt, user_id, row)
        elif row.status == "open":
            await _finish(runtime, rt, user_id, row, status, body.worked_minutes)
    async with rt.session_factory() as db:
        return await session_out(db, user_id, study_id)

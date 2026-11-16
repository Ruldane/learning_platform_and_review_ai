"""Lancer un relevé du radar (P10, D160), sous le verrou des relevés de l'utilisatrice : un seul
relevé en cours (409 `radar_in_progress`) ; un relevé `running` dont la session n'est plus ouverte
passe en `failed` d'abord (le statut suit la session, comme D129 n° 5, et se corrige à la
lecture) ; sans poste, 409 `radar_role_required`. Le poste et la zone donnés sont mémorisés dans
les réglages. Journaux : identifiants, nombres et codes seulement, jamais le poste ni la zone."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.daily import RadarTrigger
from app.features.learning.service.goals import list_goals
from app.features.ledger.service.ledger import safe_code
from app.features.radar.repository import RadarRunRepository
from app.features.radar.schemas import RadarRunIn, RunStarted
from app.features.radar.service.runtime import GRAPH, SUBJECT, RadarRuntime
from app.features.sessions.service import list_open_sessions_by_subject, session_facts
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

DEFAULT_ZONE = "France"
LAUNCH_FAILED = "launch_failed"
SESSION_CANCELLED = "session_cancelled"
_DEAD_CODES = {
    "failed": "session_failed",
    "cancelled": SESSION_CANCELLED,
    "completed": "not_finalized",
}


def radar_in_progress(run_id: str) -> AppError:
    return AppError(
        "radar_in_progress",
        "Un relevé du radar est déjà en cours : attends sa fin.",
        409,
        {"run_id": run_id},
    )


def radar_role_required() -> AppError:
    return AppError(
        "radar_role_required",
        "Indique le poste visé pour lancer un relevé du radar.",
        409,
    )


def radar_run_not_found() -> AppError:
    return AppError("radar_run_not_found", "Relevé du radar introuvable.", 404)


async def defaults(db: AsyncSession, user_id: str) -> tuple[str, str]:
    """`(poste, zone)` par défaut : les réglages, sinon le poste visé du dernier objectif ;
    zone « France » sans réglage. Le poste peut être vide."""
    settings = await SettingsService(db, user_id).get()
    role = settings.radar_role.strip()
    if not role:
        goals = await list_goals(db, user_id)
        role = (goals[0].target_role or "").strip() if goals else ""
    return role, settings.radar_zone.strip() or DEFAULT_ZONE


def _dead_code(status: str | None) -> str:
    return LAUNCH_FAILED if status is None else _DEAD_CODES.get(status, "session_ended")


async def settle(db: AsyncSession, user_id: str, now: datetime) -> None:
    """Les relevés `running` sans session ouverte passent en `failed`, avec un code lisible
    (`session_failed`, `session_cancelled`, `not_finalized`, `launch_failed`). Sessions lues AVANT
    les relevés (D97 n° 9). L'appelant tient `runs_lock`."""
    open_ids = await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)
    changed = False
    for row in await RadarRunRepository(db, user_id).running():
        if row.session_id is not None and row.session_id in open_ids.get(row.id, []):
            continue
        facts = await session_facts(db, user_id, row.session_id) if row.session_id else None
        row.status, row.error_code = "failed", _dead_code(facts.status if facts else None)
        row.finished_at = now
        changed = True
        logger.info("Relevé sans session : utilisateur %s, relevé %s", user_id, row.id)
    if changed:
        await db.commit()


async def settled(rt: RadarRuntime, user_id: str) -> None:
    """`settle` sous le verrou des relevés, dans sa propre session : à appeler avant toute lecture
    qui montre un statut."""
    async with rt.runs_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id, rt.now())


async def _resolve(db: AsyncSession, user_id: str, body: RadarRunIn) -> tuple[str, str]:
    """Poste et zone du relevé ; ceux que la requête donne sont mémorisés dans les réglages."""
    default_role, default_zone = await defaults(db, user_id)
    role, zone = body.role or default_role, body.zone or default_zone
    if not role:
        raise radar_role_required()
    if body.role or body.zone:
        service = SettingsService(db, user_id)
        current = await service.get()
        await service.replace(current.model_copy(update={"radar_role": role, "radar_zone": zone}))
    return role, zone


async def _mark_failed(rt: RadarRuntime, user_id: str, run_id: str, code: str) -> None:
    async with rt.session_factory() as db:
        row = await RadarRunRepository(db, user_id).get_fresh(run_id)
        if row is not None and row.status == "running":
            row.status, row.error_code, row.finished_at = "failed", safe_code(code), rt.now()
            await db.commit()


async def _launch(rt: RadarRuntime, user_id: str, run_id: str) -> RunStarted:
    try:
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"run_id": run_id}, subject_type=SUBJECT, subject_id=run_id
        )
    except BaseException as exc:
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        await _mark_failed(rt, user_id, run_id, code)
        logger.warning("Relevé non lancé : utilisateur %s, relevé %s", user_id, run_id)
        raise
    async with rt.session_factory() as db:
        row = await RadarRunRepository(db, user_id).get_fresh(run_id)
        if row is not None:
            row.session_id = session_id
            await db.commit()
    logger.info("Relevé lancé : utilisateur %s, relevé %s, session %s", user_id, run_id, session_id)
    return RunStarted(run_id=run_id, session_id=session_id)


async def start_run(
    rt: RadarRuntime,
    user_id: str,
    body: RadarRunIn,
    *,
    trigger: RadarTrigger,
    period: str | None,
) -> RunStarted:
    """Crée le relevé puis lance le parcours `market_radar` (sujet `radar_run`, limite de pas fixée
    par le parcours). 409 `radar_in_progress` (`details.run_id`) ou `radar_role_required`."""
    async with rt.runs_lock(user_id):
        async with rt.session_factory() as db:
            await settle(db, user_id, rt.now())
            running = await RadarRunRepository(db, user_id).running()
            if running:
                raise radar_in_progress(running[0].id)
            role, zone = await _resolve(db, user_id, body)
            row = await RadarRunRepository(db, user_id).add(
                role=role,
                zone=zone,
                role_norm=normalize_skill_name(role)[:120],
                zone_norm=normalize_skill_name(zone)[:120],
                trigger=trigger,
                period=period,
                status="running",
            )
            run_id = row.id
            await db.commit()
        return await _launch(rt, user_id, run_id)

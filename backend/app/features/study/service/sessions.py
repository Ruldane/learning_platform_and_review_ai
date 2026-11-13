"""Départ d'une session guidée (SPEC F14, D103) : « Commencer mon bloc » (bloc du jour) ou une
leçon choisie, avec ou sans question pour le Tuteur.

Sous le verrou de l'utilisatrice : la leçon (404 `lesson_not_found`, 409 `lesson_not_ready`) ou
le bloc du jour (404 `no_block_today`, seulement s'il n'y a pas de session ouverte : « Commencer
mon bloc » sans bloc, avec une session vivante, rend 409 `study_already_open` vers elle) ; une
session `open` dont la session d'agents est terminée passe à `cancelled` dans la même
transaction que l'insertion de la nouvelle (F11) ; une session vivante sur la même leçon est
rendue telle quelle (200), sur une autre leçon : 409 `study_already_open`
(`details.study_session_id`). L'index unique partiel tranche une course qui passerait quand
même : le second relit la session ouverte. La ligne est commitée AVANT `launcher.start` (jamais
le verrou d'écriture de SQLite tenu pendant le lancement, D66, D72) ; un lancement refusé
laisse la session `cancelled`. Journaux : identifiants seulement."""

import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.schemas import StudyStart, StudyStarted
from app.features.study.service.block import block_of_day, module_block
from app.features.study.service.runtime import GRAPH, SUBJECT, StudyRuntime
from app.features.study.service.store import lesson_not_ready
from app.features.study.service.view import agent_status, is_dead

logger = logging.getLogger(__name__)


def lesson_not_found() -> AppError:
    return AppError("lesson_not_found", "Leçon introuvable.", 404)


def no_block_today() -> AppError:
    return AppError("no_block_today", "Rien de prévu aujourd'hui : choisis une leçon.", 404)


def study_already_open(study_id: str) -> AppError:
    return AppError(
        "study_already_open",
        "Une session d'étude est déjà ouverte sur une autre leçon : termine-la d'abord.",
        409,
        {"study_session_id": study_id},
    )


@dataclass(frozen=True)
class Target:
    lesson_id: str
    module_id: str
    program_id: str
    task_ids: list[str]


async def _target(
    rt: StudyRuntime, db: AsyncSession, user_id: str, body: StudyStart
) -> Target | None:
    """La cible du départ ; `None` : « mon bloc » sans bloc du jour."""
    today = await rt.today(db, user_id)
    if body.lesson_id is None:
        block = await block_of_day(db, user_id, today)
        if block is None:
            return None
        return Target(block.lesson_id, block.module_id, block.program_id, block.task_ids)
    lesson = await StudyReadRepository(db, user_id).lesson(body.lesson_id)
    if lesson is None:
        raise lesson_not_found()
    if lesson.status != "ready":
        raise lesson_not_ready()
    tasks = await module_block(db, user_id, lesson.module_id, today)
    return Target(lesson.id, lesson.module_id, lesson.program_id, tasks)


async def _live(db: AsyncSession, user_id: str) -> tuple[str, str, str] | None:
    """`(id, leçon, session)` de la session ouverte encore vivante ; une session morte (sa
    session d'agents est terminée, ou son lancement s'est arrêté : sous le verrou, une session
    sans session d'agents n'est plus en cours de lancement) passe à `cancelled` (F11), non
    commitée."""
    repo = StudyRepository(db, user_id)
    row = await repo.open_one()
    if row is None:
        return None
    status = await agent_status(db, user_id, row.session_id)
    if row.session_id is None or is_dead(row, status):
        await repo.close_open(row.id, status="cancelled")
        logger.info("Session d'étude interrompue annulée : étude %s", row.id)
        return None
    return row.id, row.lesson_id, row.session_id


def _existing(live: tuple[str, str, str], lesson_id: str | None) -> StudyStarted:
    """La session ouverte rendue telle quelle ; autre leçon, ou pas de leçon (pas de bloc) : 409."""
    study_id, open_lesson, session_id = live
    if open_lesson != lesson_id:
        raise study_already_open(study_id)
    return StudyStarted(study_session_id=study_id, session_id=session_id, lesson_id=lesson_id)


async def _insert(
    rt: StudyRuntime, user_id: str, body: StudyStart
) -> tuple[StudyStarted | None, str, str]:
    """Sous le verrou : `(session rendue telle quelle, None, None)` ou `(None, id, leçon)` de
    la session insérée et commitée."""
    async with rt.session_factory() as db:
        target = await _target(rt, db, user_id, body)
        live = await _live(db, user_id)
        if live is not None:
            return _existing(live, target.lesson_id if target else None), "", ""
        if target is None:
            raise no_block_today()
        repo = StudyRepository(db, user_id)
        try:
            row = await repo.add(
                lesson_id=target.lesson_id,
                module_id=target.module_id,
                program_id=target.program_id,
                mode=body.mode,
                status="open",
                question=(body.question or "").strip() or None,
                task_ids=target.task_ids,
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            live = await _live(db, user_id)
            if live is None:
                raise
            return _existing(live, target.lesson_id), "", ""
        return None, row.id, target.lesson_id


async def _set_session(rt: StudyRuntime, user_id: str, study_id: str, sid: str | None) -> None:
    async with rt.session_factory() as db:
        repo = StudyRepository(db, user_id)
        if sid is None:
            await repo.close_open(study_id, status="cancelled")
        else:
            await repo.update(study_id, session_id=sid)
        await db.commit()


async def start_study(
    rt: StudyRuntime, user_id: str, body: StudyStart
) -> tuple[StudyStarted, bool]:
    """Ouvre la session et lance le Tuteur ; rend `(départ, créée)` (créée : 202, sinon 200)."""
    async with rt.study_lock(user_id):
        existing, study_id, lesson_id = await _insert(rt, user_id, body)
        if existing is not None:
            return existing, False
        try:
            sid = await rt.launcher.start(
                user_id,
                GRAPH,
                {"study_session_id": study_id},
                subject_type=SUBJECT,
                subject_id=study_id,
            )
        except BaseException:
            await _set_session(rt, user_id, study_id, None)
            raise
        await _set_session(rt, user_id, study_id, sid)
    logger.info("Session d'étude ouverte : étude %s, session %s", study_id, sid)
    return StudyStarted(study_session_id=study_id, session_id=sid, lesson_id=lesson_id), True

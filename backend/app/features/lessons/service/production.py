"""Production des leçons en chaîne (SPEC 3.5, 3.6 ; D90, D91).

Une seule chaîne `lesson_factory` par programme, un module à la fois (pas de rafale d'appels au
modèle) : `ensure_lessons` lance la leçon du premier module dû si aucune session de leçon n'est
ouverte pour le programme. Elle est appelée par la validation (semaines 1 et 2 tout de suite),
par la fin de chaque leçon (`next_module`, qui exclut sa propre session) et par la tâche
planifiée (semaines suivantes 7 jours avant leur début). Tout passe sous le verrou des leçons du
programme : deux appels simultanés ne lancent jamais deux sessions, ni deux leçons d'un module.

Une session de leçon qui s'arrête sans passer par le port (Vérificateur invalide, quota,
annulation…) laisse sa leçon `generating` : la leçon passe en échec au prochain appel (sa
session n'est plus ouverte), au plus tard au passage suivant de la tâche (15 minutes) ; les
lectures la montrent en échec dès l'arrêt (`status`). Une leçon en échec est relancée tant
qu'elle a eu moins de `MAX_ATTEMPTS` essais, après les modules jamais tentés. Sans rien de dû,
un appel ne fait que lire la base : ni écriture, ni lancement, ni appel au modèle. Journaux :
identifiants seulement."""

import logging
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.service.runtime import Launcher
from app.features.lessons.service.status import GRAPH, INTERRUPTED, SUBJECT
from app.features.program.service.programs import Loaded, list_validated_programs, load
from app.features.sessions.service import list_open_sessions

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
HORIZON_DAYS = 7
FIRST_WEEKS = (1, 2)


class ProductionContext(Protocol):
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]: ...

    @property
    def launcher(self) -> Launcher: ...

    def lessons_lock(self, user_id: str, program_id: str) -> AbstractAsyncContextManager[None]: ...


@dataclass(frozen=True)
class _Pick:
    lesson_id: str
    module_id: str
    # Statut, essais et raison d'avant : rétablis si le lancement échoue.
    previous: tuple[str, int, str | None]


def week_due(rank: int, start: date, today: date) -> bool:
    """Semaines 1 et 2 tout de suite, les suivantes dès 7 jours avant leur début (UTC)."""
    return rank in FIRST_WEEKS or start <= today + timedelta(days=HORIZON_DAYS)


def _missing_lessons(db: AsyncSession, user_id: str, loaded: Loaded, have: set[str]) -> int:
    """Une leçon `pending` pour chaque module planifié qui n'en a pas (liste des leçons) ;
    rend le nombre de leçons ajoutées (zéro hors de la première passe après la validation)."""
    missing = [m for m in loaded.modules if not m.skipped and m.id not in have]
    for module in missing:
        db.add(
            Lesson(
                user_id=user_id,
                module_id=module.id,
                program_id=loaded.program.id,
                title=module.title[:200],
                status="pending",
            )
        )
    return len(missing)


def _reconcile(lessons: list[Lesson], open_ids: list[str]) -> int:
    """Leçon `generating` dont la session n'est plus ouverte : en échec (relancée ensuite)."""
    stale = [x for x in lessons if x.status == "generating" and x.session_id not in open_ids]
    for lesson in stale:
        lesson.status, lesson.failure_reason = "failed", INTERRUPTED
    return len(stale)


def _first_due(loaded: Loaded, lessons: dict[str, Lesson], today: date) -> Lesson | None:
    """Premier module dû : jamais tentés d'abord, puis en échec ; par semaine puis rang."""
    weeks = {week.id: week for week in loaded.weeks}
    due: list[tuple[bool, int, Lesson]] = []
    for index, module in enumerate(loaded.modules):
        week = weeks.get(module.week_id)
        lesson = lessons.get(module.id)
        if module.skipped or week is None or lesson is None:
            continue
        if lesson.status not in ("pending", "failed") or lesson.attempts >= MAX_ATTEMPTS:
            continue
        if week_due(week.rank, week.start_date, today):
            due.append((lesson.status == "failed", index, lesson))
    return min(due, key=lambda item: (item[0], item[1]))[2] if due else None


async def _prepare(
    db: AsyncSession, user_id: str, program_id: str, exclude: str | None, today: date
) -> _Pick | None:
    loaded = await load(db, user_id, program_id)
    if loaded.program.status != "validated":
        return None
    repo = LessonRepository(db, user_id)
    rows = await repo.for_program(program_id)
    if _missing_lessons(db, user_id, loaded, {x.module_id for x in rows}):
        await db.flush()
        rows = await repo.for_program(program_id)
    open_ids = await list_open_sessions(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=program_id
    )
    if stale := _reconcile(rows, open_ids):
        logger.info("Leçons interrompues : programme %s, %d en échec", program_id, stale)
    if any(session_id != exclude for session_id in open_ids):
        return None  # une chaîne tourne déjà pour ce programme
    lesson = _first_due(loaded, {x.module_id: x for x in rows}, today)
    if lesson is None:
        return None
    pick = _Pick(
        lesson.id, lesson.module_id, (lesson.status, lesson.attempts, lesson.failure_reason)
    )
    lesson.status, lesson.attempts = "generating", lesson.attempts + 1
    lesson.failure_reason, lesson.session_id = None, None
    return pick


async def _set_session(ctx: ProductionContext, user_id: str, pick: _Pick, sid: str | None) -> None:
    """Session lancée rangée sur la leçon ; `None` : lancement raté, état d'avant rétabli."""
    async with ctx.session_factory() as db:
        lesson = await LessonRepository(db, user_id).get_fresh(pick.lesson_id)
        if lesson is not None:
            if sid is None:
                lesson.status, lesson.attempts, lesson.failure_reason = pick.previous
            else:
                lesson.session_id = sid
        await db.commit()


async def ensure_lessons(
    ctx: ProductionContext,
    user_id: str,
    program_id: str,
    *,
    exclude_session_id: str | None = None,
    today: date | None = None,
) -> str | None:
    """Lance la leçon du premier module dû si aucune autre session de leçon n'est ouverte pour le
    programme ; rend l'id de la session lancée, `None` sinon. Programme d'un autre : 404.
    Lancement refusé (moteur indisponible) : la leçon retrouve son état et l'erreur remonte."""
    day = today or datetime.now(UTC).date()
    async with ctx.lessons_lock(user_id, program_id):
        async with ctx.session_factory() as db:
            pick = await _prepare(db, user_id, program_id, exclude_session_id, day)
            await db.commit()
        if pick is None:
            return None
        payload = {"program_id": program_id, "module_id": pick.module_id}
        try:
            sid = await ctx.launcher.start(
                user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=program_id
            )
        except BaseException:
            await _set_session(ctx, user_id, pick, None)
            raise
        await _set_session(ctx, user_id, pick, sid)
    logger.info(
        "Leçon lancée : utilisateur %s, programme %s, module %s, session %s",
        user_id,
        program_id,
        pick.module_id,
        sid,
    )
    return sid


async def start_lessons(ctx: ProductionContext, user_id: str, program_id: str) -> None:
    """`ensure_lessons` sans jamais lever (après une validation) : une panne est journalisée
    par son type, la tâche planifiée rattrapera."""
    try:
        await ensure_lessons(ctx, user_id, program_id)
    except Exception as exc:
        logger.warning("Leçons non lancées : programme %s (%s)", program_id, type(exc).__name__)


async def list_programs_due(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[tuple[str, str]]:
    """`(utilisateur, programme)` des programmes validés : seule lecture sans `user_id` de la
    phase, réservée à la tâche planifiée (D91), identifiants seulement."""
    async with session_factory() as db:
        return await list_validated_programs(db)

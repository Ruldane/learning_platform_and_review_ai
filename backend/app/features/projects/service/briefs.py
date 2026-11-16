"""Les énoncés des mini projets (P1, D166) : un projet par module non sauté d'un programme validé,
créé quand la semaine du module a commencé (lundi local ≤ aujourd'hui), par la tâche planifiée
`project_briefs` (`app.scheduler`, jamais importé ici : contrat 8), toutes les 15 minutes et au
démarrage. Un passage ne crée (donc ne lance) que `MAX_NEW_PER_PASS` projets par compte, les
semaines les plus anciennes d'abord : sur un programme déjà avancé, les énoncés partent trois par
trois, toutes les 15 minutes, au lieu d'un mur d'appels au même instant (D173).

La lecture des programmes validés de tous les comptes (`list_validated_programs`, D91) est la
seule lecture sans `user_id` ; tout le reste se fait compte par compte. La création est gardée en
SQL (`ON CONFLICT (user_id, module_id) DO NOTHING`) : **seul celui qui insère lance** la session
`project_brief`, deux passages ne font donc qu'un projet et qu'une session. Chaque passage
corrige aussi les projets dont la session est morte (`settle_all`) et relance un énoncé qui n'a
pas abouti, trois essais au plus, puis `brief_failed` (« Réessayer » : `POST /projects/{id}/brief`).
Une panne pour un compte n'arrête pas les autres. Journaux : identifiants et nombres."""

import logging
from datetime import date, datetime

from app.core.clock import local_today, user_zone
from app.features.program.service.programs import list_validated_programs, load
from app.features.projects.repository import ProjectRepository
from app.features.projects.schemas import SessionStarted
from app.features.projects.service.errors import (
    brief_not_failed,
    brief_unavailable,
    project_not_found,
)
from app.features.projects.service.launch import start_brief_session
from app.features.projects.service.rules import week_started
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.settle import settle_all
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

MAX_NEW_PER_PASS = 3


async def _create_missing(
    rt: ProjectsRuntime, user_id: str, programs: list[str], now: datetime
) -> list[str]:
    """Les projets créés (ids) pour les modules non sautés dont la semaine a commencé."""
    created: list[str] = []
    async with rt.session_factory() as db:
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        today = local_today(zone, now)
        repo = ProjectRepository(db, user_id)
        known = await repo.module_ids()
        due: list[tuple[date, str, str, str]] = []  # (début de semaine, programme, module, titre)
        for program_id in programs:
            loaded = await load(db, user_id, program_id)
            starts = {week.id: week.start_date for week in loaded.weeks}
            for module in loaded.modules:
                start = starts.get(module.week_id)
                if module.skipped or module.id in known or start is None:
                    continue
                if week_started(start, today):
                    due.append((start, program_id, module.id, module.title))
        for _, program_id, module_id, title in sorted(due)[:MAX_NEW_PER_PASS]:
            project_id = await repo.insert_if_absent(
                module_id=module_id, program_id=program_id, title=title, now=now
            )
            if project_id is not None:
                created.append(project_id)
        await db.commit()
    return created


async def _ensure_user(
    rt: ProjectsRuntime, user_id: str, programs: list[str], now: datetime
) -> int:
    async with rt.ensure_lock(user_id):
        created = await _create_missing(rt, user_id, programs, now)
        for project_id in created:
            async with rt.project_lock(user_id, project_id):
                await start_brief_session(rt, user_id, project_id)
        await settle_all(rt, user_id, retry=True)
    return len(created)


async def ensure_project_briefs(rt: ProjectsRuntime, now: datetime) -> int:
    """Un passage de la tâche planifiée ; rend le nombre de projets créés (un énoncé lancé
    chacun)."""
    async with rt.session_factory() as db:
        pairs = await list_validated_programs(db)
    by_user: dict[str, list[str]] = {}
    for user_id, program_id in pairs:
        by_user.setdefault(user_id, []).append(program_id)
    created = 0
    for user_id, programs in by_user.items():
        try:
            created += await _ensure_user(rt, user_id, programs, now)
        except Exception as exc:
            logger.warning("Énoncés : utilisateur %s non traité (%s)", user_id, type(exc).__name__)
    level = logging.INFO if created else logging.DEBUG
    logger.log(level, "Énoncés : %d compte(s), %d projet(s) créé(s)", len(by_user), created)
    return created


async def retry_brief(rt: ProjectsRuntime, user_id: str, project_id: str) -> SessionStarted:
    """« Réessayer » : un énoncé en échec repart pour trois essais de plus ; 409
    `brief_not_failed` sinon, 503 si le moteur refuse le lancement (le projet reste en échec)."""
    async with rt.project_lock(user_id, project_id):
        async with rt.session_factory() as db:
            row = await ProjectRepository(db, user_id).get_fresh(project_id)
            if row is None:
                raise project_not_found()
            if row.status != "brief_failed":
                raise brief_not_failed()
            row.status, row.brief_attempts, row.session_id = "brief_pending", 1, None
            await db.commit()
        session_id = await start_brief_session(rt, user_id, project_id)
        if session_id is None:
            async with rt.session_factory() as db:
                row = await ProjectRepository(db, user_id).get_fresh(project_id)
                if row is not None:
                    row.status = "brief_failed"
                    await db.commit()
            raise brief_unavailable()
    return SessionStarted(session_id=session_id)

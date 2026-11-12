"""Port des leçons (`LessonStore`, D90) sur la feature `lessons` : implémentation branchée par
`bootstrap.agent_ports` (D91). Chaque appel ouvre sa propre session de base, courte, et la
commite (D66) ; chaque appel vérifie que le module est à l'utilisateur (404 sinon).

Écritures idempotentes par module (SPEC 9.4) : `publish` rejoué rend la même leçon sans ligne de
plus et rattrape ses suites manquées (copies, PDF, mémoire) ; `fail` ne touche jamais une leçon
prête ; `next_module` passe par `ensure_lessons` (une seule chaîne par programme). Journaux :
identifiants seulement (SPEC 17.2)."""

import logging
import re
from collections.abc import Sequence
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_port import (
    MAX_SEED_URLS,
    LessonReport,
    ModuleBrief,
    PublishedLesson,
    ResourcePick,
)
from app.db.models.lessons import Lesson
from app.db.models.program import Module
from app.db.models.research import Source
from app.features.learning.service.goals import owned_goal
from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.service.production import ensure_lessons
from app.features.lessons.service.publishing import Published, finish
from app.features.lessons.service.resources import upsert_resources
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.program.service.programs import Loaded, load, program_of_module
from app.features.research.service.reading import list_sources
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

_WORD = re.compile(r"\w{4,}")
MAX_FAILURE = 300


def _words(text: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(text)}


def seed_urls(module: Module, sources: Sequence[Source]) -> tuple[str, ...]:
    """Pages retenues et praticiens du Conseil, ceux qui parlent du module d'abord (mots du
    titre et des compétences dans leur titre ou leur résumé), puis par note ; 5 au plus."""
    wanted = _words(" ".join([module.title, *map(str, module.skills)]))
    usable = [s for s in sources if s.kind == "person" or s.verdict == "kept"]

    def rank(source: Source) -> tuple[int, int]:
        found = _words(f"{source.title or ''} {source.summary or ''}")
        return (-len(wanted & found), -(source.score or 0))

    seeds: list[str] = []
    for source in sorted(usable, key=rank):
        if source.url not in seeds:
            seeds.append(source.url)
    return tuple(seeds[:MAX_SEED_URLS])


def _module(loaded: Loaded, module_id: str) -> Module:
    return next(m for m in loaded.modules if m.id == module_id)


async def _lesson(db: AsyncSession, user_id: str, loaded: Loaded, module: Module) -> Lesson:
    """La leçon du module (créée si la production ne l'a pas encore fait)."""
    repo = LessonRepository(db, user_id)
    lesson = await repo.by_module(module.id)
    if lesson is None:
        lesson = await repo.add(
            module_id=module.id, program_id=loaded.program.id, title=module.title[:200]
        )
    return lesson


class AgentLessonStore:
    def __init__(self, runtime: LessonsRuntime) -> None:
        self._rt = runtime

    async def brief(self, user_id: str, module_id: str) -> ModuleBrief:
        async with self._rt.session_factory() as db:
            loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
            module = _module(loaded, module_id)
            week = next(w for w in loaded.weeks if w.id == module.week_id)
            goal = await owned_goal(db, user_id, loaded.program.goal_id)
            settings = await SettingsService(db, user_id).get()
            council = goal.council_session_id
            sources = await list_sources(db, user_id, council) if council else []
            return ModuleBrief(
                module_id=module.id,
                program_id=loaded.program.id,
                title=module.title,
                skills=tuple(str(s) for s in module.skills),
                prerequisites=tuple(str(p) for p in module.prerequisites),
                week_rank=week.rank,
                week_theme=week.theme,
                goal_text=goal.text,
                language=settings.lesson_language,
                seed_urls=seed_urls(module, sources),
            )

    async def _save(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        module_id: str,
        markdown: str,
        picks: Sequence[ResourcePick],
        report: LessonReport,
    ) -> Published:
        loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
        module = _module(loaded, module_id)
        lesson = await _lesson(db, user_id, loaded, module)
        if lesson.status != "ready":
            sources = {s.id: s for s in await list_sources(db, user_id, session_id)}
            await upsert_resources(
                db,
                user_id,
                module_id=module_id,
                program_id=loaded.program.id,
                picks=picks,
                sources=sources,
            )
            lesson.status, lesson.markdown, lesson.word_count = "ready", markdown, report.words
            lesson.report, lesson.failure_reason = asdict(report), None
            lesson.session_id = session_id
        language = (await SettingsService(db, user_id).get()).lesson_language
        return Published(
            user_id,
            lesson.session_id or session_id,
            lesson.id,
            module_id,
            lesson.title,
            lesson.markdown,
            language,
            loaded.program.title,
        )

    async def publish(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        *,
        markdown: str,
        resources: Sequence[ResourcePick],
        report: LessonReport,
    ) -> PublishedLesson:
        async with self._rt.session_factory() as db:
            done = await self._save(db, user_id, session_id, module_id, markdown, resources, report)
            await db.commit()
        pdf_ok = await finish(self._rt, done)
        async with self._rt.session_factory() as db:
            count = len(await ResourceRepository(db, user_id).for_module(module_id))
        logger.info(
            "Leçon rangée : session %s, module %s, leçon %s, %d ressource(s)",
            session_id,
            module_id,
            done.lesson_id,
            count,
        )
        return PublishedLesson(done.lesson_id, pdf_ok, count)

    async def fail(self, user_id: str, session_id: str, module_id: str, reason: str) -> None:
        async with self._rt.session_factory() as db:
            loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
            lesson = await _lesson(db, user_id, loaded, _module(loaded, module_id))
            if lesson.status != "ready":
                lesson.status, lesson.failure_reason = "failed", reason.strip()[:MAX_FAILURE]
                lesson.session_id = session_id
            await db.commit()
        logger.info("Leçon en échec : session %s, module %s", session_id, module_id)

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        """La session lancée pour le module suivant (son id), `None` s'il n'y en a pas."""
        return await ensure_lessons(
            self._rt, user_id, program_id, exclude_session_id=exclude_session_id
        )

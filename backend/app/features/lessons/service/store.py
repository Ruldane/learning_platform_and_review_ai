"""Lessons port (`LessonStore`, D90) on the `lessons` feature: implementation wired by
`bootstrap.agent_ports` (D91). Each call opens its own short database session and commits it
(D66); each call checks that the module belongs to the user (404 otherwise).

Idempotent writes per module (SPEC 9.4): a replayed `publish` returns the same lesson with no
extra row and catches up on its missed follow-ups (copies, PDF, memory); `fail` never touches a
ready lesson; `next_module` goes through `ensure_lessons` (a single chain per program). Logs:
identifiers only (SPEC 17.2)."""

import logging
import re
from collections.abc import Sequence
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_port import (
    MAX_SEED_URLS,
    LessonReport,
    LessonSubmission,
    ModuleBrief,
    PublishedLesson,
    ResourcePick,
)
from app.db.models.lessons import Lesson
from app.db.models.program import Module
from app.db.models.research import Source
from app.features.learning.service.goals import owned_goal
from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.service.chapter_context import chapter_context
from app.features.lessons.service.production import ensure_lessons
from app.features.lessons.service.publishing import Published, finish
from app.features.lessons.service.resources import upsert_resources
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.verification import (
    RevisionPdfUnavailable,
    fail_submission,
    prepare_pdf,
    save_submission,
    submission,
    verification_revoked,
)
from app.features.memory.service.direct import schedule_indexing
from app.features.program.service.programs import Loaded, load, program_of_module
from app.features.research.service.reading import list_sources
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

_WORD = re.compile(r"\w{4,}")
MAX_FAILURE = 300


def _words(text: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(text)}


def seed_urls(module: Module, sources: Sequence[Source]) -> tuple[str, ...]:
    """The module's official pages first, then the Council's kept pages and practitioners, those
    about the module first (words of the title and skills in their title or summary), then by
    score; no duplicates, 5 at most."""
    wanted = _words(" ".join([module.title, *map(str, module.skills)]))
    usable = [s for s in sources if s.kind == "person" or s.verdict == "kept"]

    def rank(source: Source) -> tuple[int, int]:
        found = _words(f"{source.title or ''} {source.summary or ''}")
        return (-len(wanted & found), -(source.score or 0))

    seeds: list[str] = []
    for url in (str(u) for u in module.official_urls):
        if url not in seeds:
            seeds.append(url)
    for source in sorted(usable, key=rank):
        if source.url not in seeds:
            seeds.append(source.url)
    return tuple(seeds[:MAX_SEED_URLS])


def _module(loaded: Loaded, module_id: str) -> Module:
    return next(m for m in loaded.modules if m.id == module_id)


async def _lesson(db: AsyncSession, user_id: str, loaded: Loaded, module: Module) -> Lesson:
    """The module's lesson (created if production has not done so yet)."""
    repo = LessonRepository(db, user_id)
    lesson = await repo.by_module(module.id)
    if lesson is None:
        lesson = await repo.add(
            module_id=module.id, program_id=loaded.program.id, title=module.title[:200]
        )
    return lesson


async def _save_generated(
    db: AsyncSession,
    lesson: Lesson,
    session_id: str,
    markdown: str,
    picks: Sequence[ResourcePick],
    report: LessonReport,
) -> None:
    if lesson.status == "ready":
        return
    if lesson.verification_session_id is not None:
        raise verification_revoked()
    await upsert_resources(
        db,
        lesson.user_id,
        module_id=lesson.module_id,
        program_id=lesson.program_id,
        picks=picks,
        sources={s.id: s for s in await list_sources(db, lesson.user_id, session_id)},
    )
    lesson.status, lesson.markdown, lesson.word_count = "ready", markdown, report.words
    lesson.report, lesson.failure_reason, lesson.session_id = asdict(report), None, session_id


class AgentLessonStore:
    def __init__(self, runtime: LessonsRuntime) -> None:
        self._rt = runtime

    async def submission(self, user_id: str, session_id: str, module_id: str) -> LessonSubmission:
        async with self._rt.session_factory() as db:
            return await submission(db, user_id, session_id, module_id)

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
                chapter_context=await chapter_context(db, user_id, loaded, module),
                legacy=tuple(str(n) for n in module.legacy),
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
        *,
        verification: bool,
        pdf_key: str | None,
    ) -> Published:
        repo = LessonRepository(db, user_id)
        candidate = (
            await repo.claim_verification(module_id, session_id, replay=True)
            if verification
            else None
        )
        if verification and candidate is None:
            raise verification_revoked()
        loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
        module = _module(loaded, module_id)
        lesson = candidate or await _lesson(db, user_id, loaded, module)
        if verification:
            try:
                await save_submission(
                    db, self._rt, lesson, loaded.program.title, markdown, picks, report, pdf_key
                )
            except RevisionPdfUnavailable as exc:
                await fail_submission(db, user_id, session_id, module_id, exc.message)
                await (
                    db.commit()
                )  # the rejection releases the reservation in the publication transaction
                raise
        else:
            await _save_generated(db, lesson, session_id, markdown, picks, report)
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
            lesson.pdf_key,
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
        verification: bool = False,
    ) -> PublishedLesson:
        async with self._rt.session_factory() as db:
            program_id = await program_of_module(db, user_id, module_id)
        key = (
            await prepare_pdf(self._rt, user_id, module_id, session_id, markdown)
            if verification
            else None
        )
        done = None
        try:
            async with self._rt.lessons_lock(user_id, program_id), self._rt.session_factory() as db:
                done = await self._save(
                    db,
                    user_id,
                    session_id,
                    module_id,
                    markdown,
                    resources,
                    report,
                    verification=verification,
                    pdf_key=key,
                )
                await db.commit()
        finally:
            if key is not None and (done is None or done.pdf_key != key):
                await self._rt.storage.delete(user_id, key)
        if verification:
            schedule_indexing(self._rt.memory, user_id)
        pdf_ok = done.pdf_key is not None if verification else await finish(self._rt, done)
        async with self._rt.session_factory() as db:
            count = len(await ResourceRepository(db, user_id).for_module(module_id))
        logger.info(
            "Lesson stored: session %s, module %s, lesson %s, %d resource(s)",
            session_id,
            module_id,
            done.lesson_id,
            count,
        )
        return PublishedLesson(done.lesson_id, pdf_ok, count)

    async def fail(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        reason: str,
        *,
        verification: bool = False,
        feedback: Sequence[str] = (),
    ) -> None:
        async with self._rt.session_factory() as db:
            program_id = await program_of_module(db, user_id, module_id)
        async with self._rt.lessons_lock(user_id, program_id), self._rt.session_factory() as db:
            if verification:
                await fail_submission(
                    db, user_id, session_id, module_id, reason.strip()[:MAX_FAILURE], feedback
                )
                await db.commit()
                return
            loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
            lesson = await _lesson(db, user_id, loaded, _module(loaded, module_id))
            if lesson.status != "ready" and lesson.verification_session_id is None:
                lesson.status, lesson.failure_reason = "failed", reason.strip()[:MAX_FAILURE]
                lesson.session_id = session_id
            await db.commit()
        logger.info("Lesson failed: session %s, module %s", session_id, module_id)

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        """The session started for the next module (its id), `None` if there is none."""
        return await ensure_lessons(
            self._rt, user_id, program_id, exclude_session_id=exclude_session_id
        )

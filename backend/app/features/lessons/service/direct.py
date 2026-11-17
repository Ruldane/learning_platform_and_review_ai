"""La leçon d'un module écrite en direct (phase 10, 10.W) : Claude (par le MCP) ou January fournit
le Markdown, l'application le range comme le fait le port du Rédacteur (`AgentLessonStore.publish`),
sans agent, sans session et sans appel au modèle. Sous le verrou des leçons du programme, comme la
production en chaîne : jamais deux leçons d'un module, ni une leçon écrite pendant qu'un agent
travaille sur la même.

Pas de PDF ni de copies de ressources : ce sont des fichiers hors base (rendu Gotenberg, stockage),
que l'annulation de l'historique ne reprendrait pas ; la leçon se lit dans l'application. Son texte
entre dans la mémoire (`lecon`, indexé) comme celui d'une leçon des agents."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.schemas import LessonOut, LessonPatch, LessonWriteIn
from app.features.lessons.service.lessons import get_lesson, lesson_not_found
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.status import open_lesson_sessions
from app.features.memory.service.direct import author_of, write_direct
from app.features.program.service.programs import load, program_of_module

logger = logging.getLogger(__name__)

MEMORY_REASON = "Leçon écrite directement, sans agent."


def lesson_exists() -> AppError:
    return AppError(
        "lesson_exists", "Ce module a déjà sa leçon : retouche-la (PATCH /lessons/{id}).", 409
    )


def lesson_generating() -> AppError:
    return AppError(
        "lesson_generating", "Une session écrit déjà la leçon de ce module : attends sa fin.", 409
    )


def lesson_not_ready() -> AppError:
    return AppError(
        "lesson_not_ready",
        "Cette leçon n'est pas prête : écris-la (POST /modules/{id}/lesson).",
        409,
    )


def module_skipped() -> AppError:
    return AppError("module_skipped", "Ce module est sauté : il n'a pas de leçon.", 409)


def _words(markdown: str) -> int:
    return len(markdown.split())


def _lesson_fields(lesson: Lesson, title: str, markdown: str) -> None:
    lesson.title, lesson.markdown, lesson.word_count = title, markdown, _words(markdown)


async def _remember(
    rt: LessonsRuntime,
    user_id: str,
    lesson: Lesson,
    program_title: str,
    *,
    is_mcp: bool,
    replaces: tuple[str, str] | None = None,
) -> None:
    await write_direct(
        rt.memory,
        user_id,
        kind="lecon",
        title=lesson.title,
        text=lesson.markdown,
        tags=(program_title,),
        author=author_of(is_mcp),
        reason=MEMORY_REASON,
        replaces=replaces,
    )


async def _free(db: AsyncSession, user_id: str, lesson: Lesson | None, program_id: str) -> None:
    """Refuse (409) une leçon prête, ou que l'agent est en train d'écrire."""
    if lesson is None:
        return
    if lesson.status == "ready":
        raise lesson_exists()
    open_ids = await open_lesson_sessions(db, user_id, program_id)
    if lesson.status == "generating" and lesson.session_id in (None, *open_ids):
        raise lesson_generating()


async def write_lesson(
    rt: LessonsRuntime, user_id: str, module_id: str, body: LessonWriteIn, *, is_mcp: bool
) -> LessonOut:
    """Voir le module : crée la leçon du module, ou remplit celle que la production avait posée
    (en attente ou en échec) ; 409 `lesson_exists` si elle est prête, `lesson_generating` si un
    agent l'écrit ; 404 `module_not_found` pour un module d'une autre."""
    async with rt.session_factory() as db:
        program_id = await program_of_module(db, user_id, module_id)
    async with rt.lessons_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        module = next(m for m in loaded.modules if m.id == module_id)
        if module.skipped:
            raise module_skipped()
        repo = LessonRepository(db, user_id)
        lesson = await repo.by_module(module_id)
        await _free(db, user_id, lesson, program_id)
        title = body.title or module.title[:200]
        if lesson is None:
            lesson = await repo.add(module_id=module_id, program_id=program_id, title=title)
        _lesson_fields(lesson, title, body.markdown)
        lesson.status, lesson.failure_reason, lesson.session_id = "ready", None, None
        await db.commit()
        lesson_id, program_title = lesson.id, loaded.program.title
    async with rt.session_factory() as db:
        done = await LessonRepository(db, user_id).get_fresh(lesson_id)
        assert done is not None
        await _remember(rt, user_id, done, program_title, is_mcp=is_mcp)
    logger.info(
        "Leçon écrite en direct : programme %s, module %s, leçon %s",
        program_id,
        module_id,
        lesson_id,
    )
    async with rt.session_factory() as db:
        return await get_lesson(db, user_id, lesson_id)


async def patch_lesson(
    rt: LessonsRuntime, user_id: str, lesson_id: str, patch: LessonPatch, *, is_mcp: bool
) -> LessonOut:
    """Retouche le titre ou le Markdown d'une leçon prête (409 `lesson_not_ready` sinon). Le PDF
    gardé (s'il y en a un) n'est plus celui du texte : la leçon l'oublie, le fichier reste sur le
    disque. Sa copie en mémoire est mise à jour."""
    async with rt.session_factory() as db:
        found = await LessonRepository(db, user_id).get_fresh(lesson_id)
        if found is None:
            raise lesson_not_found()
        program_id = found.program_id
    async with rt.lessons_lock(user_id, program_id), rt.session_factory() as db:
        lesson = await LessonRepository(db, user_id).get_fresh(lesson_id)
        if lesson is None:
            raise lesson_not_found()
        if lesson.status != "ready":
            raise lesson_not_ready()
        before = (lesson.title, lesson.markdown)
        title = patch.title or lesson.title
        markdown = lesson.markdown if patch.markdown is None else patch.markdown
        _lesson_fields(lesson, title, markdown)
        if markdown != before[1]:
            lesson.pdf_key = None
        loaded = await load(db, user_id, program_id)
        await db.commit()
        program_title = loaded.program.title
    if (title, markdown) != before:
        async with rt.session_factory() as db:
            done = await LessonRepository(db, user_id).get_fresh(lesson_id)
            assert done is not None
            await _remember(rt, user_id, done, program_title, is_mcp=is_mcp, replaces=before)
    async with rt.session_factory() as db:
        return await get_lesson(db, user_id, lesson_id)

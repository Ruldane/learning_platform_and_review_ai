"""Soumission d'un brouillon privé à la Fabrique et ajout immédiat de ressources (D221)."""

from collections.abc import Sequence
from typing import Any
from unicodedata import category
from urllib.parse import urlsplit

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes.lesson_reference import source_url_key
from app.agents.nodes.verifier.checks import change_heading, check_submission
from app.agents.runtime.creation import PrepareSession
from app.agents.tools.lesson_port import MAX_SEED_URLS
from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.schemas import (
    TITLE_MAX,
    LessonOut,
    LessonPatch,
    LessonWriteIn,
    ResourceWriteIn,
)
from app.features.lessons.service.lessons import get_lesson, lesson_not_found
from app.features.lessons.service.resources import attach_resources
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.status import GRAPH, SUBJECT, open_lesson_sessions
from app.features.lessons.service.versions import RevisionGuard
from app.features.program.service.programs import load, program_of_module
from app.mcp.recorder import ACTIVE


def lesson_exists() -> AppError:
    return AppError(
        "lesson_exists", "Ce module a déjà sa leçon : retouche-la (PATCH /lessons/{id}).", 409
    )


def lesson_generating() -> AppError:
    return AppError(
        "lesson_generating", "La leçon de ce module est déjà en cours de vérification.", 409
    )


def lesson_not_ready() -> AppError:
    return AppError("lesson_not_ready", "Cette leçon n'est pas encore prête.", 409)


def module_skipped() -> AppError:
    return AppError("module_skipped", "Ce module est sauté : il n'a pas de leçon.", 409)


def _draft(
    title: str, markdown: str, readings: Sequence[ResourceWriteIn], *, is_mcp: bool
) -> dict[str, Any]:
    reasons, links = check_submission(markdown, title=title)
    urls = _source_links(links, reasons)
    if any(category(char) in {"Cc", "Cf"} for char in title):
        reasons.append("Le titre doit tenir sur une seule ligne, sans caractère de contrôle.")
    if reasons:
        raise AppError(
            "lesson_invalid",
            "Le brouillon ne respecte pas la structure des leçons.",
            422,
            {"reasons": reasons[:30]},
        )
    return {
        "title": title,
        "markdown": markdown,
        "urls": urls[:MAX_SEED_URLS],
        "resources": [reading.model_dump(mode="json") for reading in readings],
        "is_mcp": is_mcp,
    }


def _source_links(links: list[str], reasons: list[str]) -> list[str]:
    urls: dict[str, str] = {}
    for link in links:
        key = source_url_key(link)
        if key is None:
            break
        parts = urlsplit(key)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
        ):
            break
        urls.setdefault(key, link)
    else:
        return list(urls.values())
    reasons.append("Les sources doivent avoir une adresse HTTP ou HTTPS sans identifiants.")
    return []


async def _active(
    db: AsyncSession, user_id: str, lesson: Lesson | None, draft: dict[str, Any]
) -> bool:
    """Une même soumission en cours rend la session existante. Toute autre attend son issue."""
    if lesson is None:
        return False
    open_ids = await open_lesson_sessions(db, user_id, lesson.program_id)
    if lesson.verification_session_id in open_ids:
        previous = dict(lesson.verification_draft or {})
        previous.pop("mcp_call_id", None)
        if previous == draft:
            return True
        raise lesson_generating()
    if (
        lesson.status == "generating"
        and lesson.verification_session_id is None
        and (lesson.session_id is None or lesson.session_id in open_ids)
    ):
        raise lesson_generating()
    return False


def _reserve(
    user_id: str,
    program_id: str,
    module_id: str,
    module_title: str,
    draft: dict[str, Any],
    *,
    revision: bool = False,
    guard: RevisionGuard | None = None,
) -> PrepareSession:
    async def prepare(db: AsyncSession, session_id: str) -> None:
        repo = LessonRepository(db, user_id)
        lesson = await repo.by_module(module_id)
        if revision and (lesson is None or lesson.status != "ready"):
            raise lesson_not_ready()
        if guard is not None and lesson is not None:
            guard.check(lesson)
            await guard.prepare(db, session_id)
        if not revision and lesson is not None and lesson.status == "ready":
            raise lesson_exists()
        if lesson is None:
            lesson = await repo.add(module_id=module_id, program_id=program_id, title=module_title)
        if not revision:
            lesson.status, lesson.session_id, lesson.failure_reason = "generating", session_id, None
        lesson.verification_session_id = session_id
        recorder = ACTIVE.get()
        lesson.verification_draft = (
            {**draft, "mcp_call_id": recorder.call_id} if recorder else draft
        )
        lesson.verification_failure_reason, lesson.verification_feedback = None, None
        if recorder is not None:
            await recorder.persist_in(db)

    return prepare


async def _submit(
    rt: LessonsRuntime, user_id: str, program_id: str, module_id: str, prepare: PrepareSession
) -> None:
    await rt.launcher.start(
        user_id,
        GRAPH,
        {"program_id": program_id, "module_id": module_id, "verification": True},
        subject_type=SUBJECT,
        subject_id=program_id,
        prepare=prepare,
    )


async def write_lesson(
    rt: LessonsRuntime, user_id: str, module_id: str, body: LessonWriteIn, *, is_mcp: bool
) -> LessonOut:
    async with rt.session_factory() as db:
        program_id = await program_of_module(db, user_id, module_id)
    async with rt.lessons_lock(user_id, program_id):
        async with rt.session_factory() as db:
            loaded = await load(db, user_id, program_id)
            module = next(m for m in loaded.modules if m.id == module_id)
            if module.skipped:
                raise module_skipped()
            lesson = await LessonRepository(db, user_id).by_module(module_id)
            if lesson is not None and lesson.status == "ready":
                raise lesson_exists()
            title = module.title[:TITLE_MAX]
            draft = _draft(body.title or title, body.markdown, body.resources, is_mcp=is_mcp)
            if await _active(db, user_id, lesson, draft) and lesson is not None:
                return await get_lesson(db, user_id, lesson.id)
        await _submit(
            rt,
            user_id,
            program_id,
            module_id,
            _reserve(user_id, program_id, module_id, title, draft),
        )
        async with rt.session_factory() as db:
            reserved = await LessonRepository(db, user_id).by_module(module_id)
            if reserved is None:
                raise lesson_not_found()
            return await get_lesson(db, user_id, reserved.id)


async def _owned(db: AsyncSession, user_id: str, lesson_id: str) -> Lesson:
    row = await LessonRepository(db, user_id).get_fresh(lesson_id)
    if row is None:
        raise lesson_not_found()
    return row


async def patch_lesson(
    rt: LessonsRuntime,
    user_id: str,
    lesson_id: str,
    patch: LessonPatch,
    *,
    is_mcp: bool,
    guard: RevisionGuard | None = None,
) -> tuple[LessonOut, bool]:
    async with rt.session_factory() as db:
        program_id = (await _owned(db, user_id, lesson_id)).program_id
    async with rt.lessons_lock(user_id, program_id):
        async with rt.session_factory() as db:
            lesson = await _owned(db, user_id, lesson_id)
            if lesson.status != "ready":
                raise lesson_not_ready()
            if guard is not None:
                guard.check(lesson)
            title = patch.title or lesson.title
            markdown = patch.markdown if patch.markdown is not None else lesson.markdown
            if (title, markdown) == (lesson.title, lesson.markdown):
                await attach_resources(
                    db,
                    user_id,
                    module_id=lesson.module_id,
                    program_id=program_id,
                    readings=patch.resources,
                )
                await db.commit()
                return await get_lesson(db, user_id, lesson_id), False
            if patch.markdown is None:
                markdown = change_heading(markdown, title)
            draft = _draft(title, markdown, patch.resources, is_mcp=is_mcp)
            if await _active(db, user_id, lesson, draft):
                return await get_lesson(db, user_id, lesson_id), True
        module_id = lesson.module_id
        reservation = _reserve(
            user_id, program_id, module_id, title, draft, revision=True, guard=guard
        )
        await _submit(rt, user_id, program_id, module_id, reservation)
        async with rt.session_factory() as db:
            return await get_lesson(db, user_id, lesson_id), True


async def submit_revision(
    rt: LessonsRuntime, user_id: str, lesson_id: str, markdown: str, guard: RevisionGuard
) -> bool:
    """Soumet la retouche approuvée d'une version précise à la vérification existante."""
    try:
        patch = LessonPatch(markdown=markdown)
    except ValidationError:
        raise AppError(
            "lesson_update_invalid", "Le brouillon de correction est invalide.", 422
        ) from None
    _, submitted = await patch_lesson(rt, user_id, lesson_id, patch, is_mcp=False, guard=guard)
    return submitted

"""Lecture et règlement d'une soumission directe par la Fabrique de leçons."""

import asyncio
from collections.abc import Sequence
from contextlib import nullcontext
from dataclasses import asdict

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_port import LessonReport, LessonSubmission, ResourcePick
from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.schemas import ResourceWriteIn
from app.features.lessons.service.publishing import render_pdf_key
from app.features.lessons.service.resources import attach_resources, upsert_resources
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.memory.service.direct import author_of, write_direct
from app.features.research.service.reading import list_sources
from app.features.settings.service import SettingsService
from app.mcp.recorder import ChangeRecorder
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S

PDF_ATTEMPT_TIMEOUT_S = 2 * HTML_RENDER_TIMEOUT_S + 10  # rendu Mermaid, repli et rangement


class RevisionPdfUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__(
            "lesson_revision_pdf_unavailable",
            "Le PDF de la retouche n'a pas pu être produit. La version publiée reste disponible.",
            503,
        )


class PendingDraft(BaseModel):
    title: str
    markdown: str
    urls: tuple[str, ...]
    resources: list[ResourceWriteIn]
    is_mcp: bool
    mcp_call_id: str | None = None


def verification_revoked() -> AppError:
    return AppError(
        "lesson_verification_revoked", "Cette session ne peut plus publier le brouillon.", 409
    )


async def submission(
    db: AsyncSession, user_id: str, session_id: str, module_id: str
) -> LessonSubmission:
    row = await LessonRepository(db, user_id).by_module(module_id)
    if row is None or row.verification_session_id != session_id:
        raise verification_revoked()
    draft = PendingDraft.model_validate(row.verification_draft)
    return LessonSubmission(draft.title, draft.markdown, draft.urls)


async def save_submission(
    db: AsyncSession,
    rt: LessonsRuntime,
    lesson: Lesson,
    program_title: str,
    markdown: str,
    picks: Sequence[ResourcePick],
    report: LessonReport,
    pdf_key: str | None,
) -> None:
    sid = lesson.verification_session_id
    if sid is None:
        return  # publication déjà commitée, les suites reprennent
    if lesson.status == "ready" and lesson.pdf_key is not None and pdf_key is None:
        raise RevisionPdfUnavailable()
    draft = PendingDraft.model_validate(lesson.verification_draft)
    recorder = (
        ChangeRecorder(rt.session_factory, draft.mcp_call_id, lesson.user_id)
        if draft.mcp_call_id
        else None
    )
    async with recorder if recorder is not None else nullcontext():
        await _save_content(db, rt, lesson, program_title, markdown, picks, draft, sid)
        lesson.title, lesson.markdown, lesson.word_count = draft.title, markdown, report.words
        lesson.status, lesson.report, lesson.failure_reason = "ready", asdict(report), None
        lesson.session_id, lesson.pdf_key = sid, pdf_key
        lesson.verification_session_id, lesson.verification_draft = None, None
        lesson.verification_feedback = None
        if recorder is not None:
            await recorder.extend_in(db, keep_latest=frozenset({"pdf_key"}))


async def _save_content(
    db: AsyncSession,
    rt: LessonsRuntime,
    lesson: Lesson,
    program_title: str,
    markdown: str,
    picks: Sequence[ResourcePick],
    draft: PendingDraft,
    sid: str,
) -> None:
    before = (lesson.title, lesson.markdown) if lesson.status == "ready" else None
    await attach_resources(
        db,
        lesson.user_id,
        module_id=lesson.module_id,
        program_id=lesson.program_id,
        readings=draft.resources,
    )
    await upsert_resources(
        db,
        lesson.user_id,
        module_id=lesson.module_id,
        program_id=lesson.program_id,
        picks=picks,
        sources={s.id: s for s in await list_sources(db, lesson.user_id, sid)},
        preserve_existing=True,
    )
    await write_direct(
        db,
        rt.memory,
        lesson.user_id,
        kind="lecon",
        title=draft.title,
        text=markdown,
        tags=(program_title,),
        author=author_of(draft.is_mcp),
        replaces=before,
        reason="Leçon soumise puis publiée après contrôle du Vérificateur.",
    )


async def prepare_pdf(
    rt: LessonsRuntime, user_id: str, module_id: str, session_id: str, markdown: str
) -> str | None:
    """Rend le futur PDF sans tenir le verrou ni publier le brouillon."""
    async with rt.session_factory() as db:
        row = await LessonRepository(db, user_id).by_module(module_id)
        if row is None or row.verification_session_id != session_id:
            return None  # rejeu d'une publication finie, ou autorisation déjà révoquée
        draft = PendingDraft.model_validate(row.verification_draft)
        language = (await SettingsService(db, user_id).get()).lesson_language
    attempts = 2 if row.status == "ready" else 1
    for _ in range(attempts):
        try:
            async with asyncio.timeout(PDF_ATTEMPT_TIMEOUT_S):
                key = await render_pdf_key(rt, user_id, row.id, draft.title, markdown, language)
        except TimeoutError:
            continue
        if key is not None:
            return key
    return None


async def fail_submission(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    module_id: str,
    reason: str,
    feedback: Sequence[str] = (),
) -> None:
    repo = LessonRepository(db, user_id)
    lesson = await repo.claim_verification(module_id, session_id)
    if lesson is None:
        # Après un arrêt entre commit et checkpoint, la même raison est déjà rangée.
        row = await repo.by_module(module_id)
        if (
            row is not None
            and row.verification_session_id is None
            and row.verification_failure_reason == reason
        ):
            return
        raise verification_revoked()
    lesson.verification_session_id, lesson.verification_draft = None, None
    lesson.verification_failure_reason = reason
    lesson.verification_feedback = list(feedback)
    if lesson.status != "ready":
        lesson.status, lesson.failure_reason = "failed", reason

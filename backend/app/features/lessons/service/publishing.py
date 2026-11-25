"""Follow-ups of a lesson's publication (D91), each idempotent and with no transaction open
during network calls (D66): local copies of the resources' free PDFs (otherwise a reading note),
the lesson's A4 PDF (Gotenberg), the lesson stored in memory (`lecon`). A failure of one is
logged by its type and blocks neither the others nor the publication: the lesson can be read in
the application and replaying the node (or the next publication) catches up on what is missing."""

import logging
from dataclasses import dataclass

from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.service.render import render_lesson_pdf
from app.features.lessons.service.resources import READING_NOTE_MAX
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.memory.service.direct import schedule_indexing, write_direct
from app.features.research.service.download import download_pdf
from app.features.research.service.reading import list_sources

logger = logging.getLogger(__name__)

AUTHOR = "writer"


@dataclass(frozen=True)
class Published:
    """What the follow-ups read back from the published lesson."""

    user_id: str
    session_id: str
    lesson_id: str
    module_id: str
    title: str
    markdown: str
    language: str
    program_title: str
    pdf_key: str | None = None


async def _pending_copies(rt: LessonsRuntime, p: Published) -> list[tuple[str, str, str | None]]:
    """`(resource, address, source)` of the resources whose copy has not been attempted yet."""
    async with rt.session_factory() as db:
        rows = await ResourceRepository(db, p.user_id).for_module(p.module_id)
    return [
        (r.id, r.url, r.source_id)
        for r in rows
        if r.local_key is None and r.note is None and r.source_id is not None
    ]


async def _notes(rt: LessonsRuntime, p: Published) -> dict[str, str]:
    """Reading note of each source of the session: its summary, otherwise its reason."""
    async with rt.session_factory() as db:
        sources = await list_sources(db, p.user_id, p.session_id)
    return {s.id: ((s.summary or s.reason or "").strip()[:READING_NOTE_MAX]) for s in sources}


async def copy_resources(rt: LessonsRuntime, p: Published) -> None:
    """Freely downloadable PDF → local copy (`resources` category), otherwise a reading note.
    A settled resource (copy or note) is not retried on replay."""
    pending = await _pending_copies(rt, p)
    if not pending:
        return
    notes = await _notes(rt, p)
    copied = 0
    for resource_id, url, source_id in pending:
        data = await download_pdf(rt.research, p.user_id, url)
        key = None if data is None else await rt.storage.save(p.user_id, "resources", data, ".pdf")
        note = notes.get(source_id or "") or "Note unavailable."
        copied += await _settle(rt, p.user_id, resource_id, key, note, publication=p)
    logger.info(
        "Resources: lesson %s, %d local copy(ies) out of %d", p.lesson_id, copied, len(pending)
    )


async def _settle(
    rt: LessonsRuntime,
    user_id: str,
    resource_id: str,
    key: str | None,
    note: str,
    *,
    publication: Published | None = None,
) -> bool:
    """Stores the copy (or, without a copy, the note) on the resource; returns "copy kept". A
    copy not kept (stored meanwhile by another call, resource gone, failed write) is deleted
    from disk: never an orphan file."""
    kept = False
    try:
        async with rt.session_factory() as db:
            if publication is not None and not await LessonRepository(db, user_id).claim_published(
                publication.lesson_id, publication.session_id
            ):
                return False
            row = await ResourceRepository(db, user_id).get(resource_id)
            claimed = row is not None and row.local_key is None
            if row is not None and claimed:
                row.local_key, row.note = key, (None if key else note)
            await db.commit()
        kept = claimed and key is not None
    finally:
        if key is not None and not kept:
            await rt.storage.delete(user_id, key)
    return kept


async def lesson_pdf(rt: LessonsRuntime, p: Published) -> bool:
    """The lesson's A4 PDF (`lessons` category), only once; `False` if still missing."""
    async with rt.session_factory() as db:
        lesson = await LessonRepository(db, p.user_id).get_fresh(p.lesson_id)
        if lesson is None or lesson.session_id != p.session_id:
            return False
        if lesson.pdf_key is not None:
            return True
    key = await render_pdf_key(rt, p.user_id, p.lesson_id, p.title, p.markdown, p.language)
    if key is None:
        return False
    async with rt.session_factory() as db:
        repo = LessonRepository(db, p.user_id)
        kept = await repo.set_pdf_key(p.lesson_id, key, p.session_id)
        lesson = await repo.get_fresh(p.lesson_id)
        await db.commit()
    if not kept:  # stored meanwhile by another call (or lesson gone): ours is redundant
        await rt.storage.delete(p.user_id, key)
    return lesson is not None and lesson.session_id == p.session_id and lesson.pdf_key is not None


async def render_pdf_key(
    rt: LessonsRuntime, user_id: str, lesson_id: str, title: str, markdown: str, language: str
) -> str | None:
    try:
        pdf = await render_lesson_pdf(
            rt.publishing.html_pdf, title=title, markdown=markdown, language=language
        )
        return await rt.storage.save(user_id, "lessons", pdf, ".pdf")
    except Exception as exc:
        logger.warning("PDF of lesson %s not produced (%s)", lesson_id, type(exc).__name__)
        return None


async def remember(rt: LessonsRuntime, p: Published) -> None:
    """The lesson in memory (`lecon`: title, Markdown, program tag); the same content replayed
    writes nothing more (memory deduplication)."""
    try:
        async with rt.session_factory() as db:
            if not await LessonRepository(db, p.user_id).claim_published(p.lesson_id, p.session_id):
                return
            await write_direct(
                db,
                rt.memory,
                p.user_id,
                kind="lesson",
                title=p.title,
                text=p.markdown,
                tags=(p.program_title,),
                author=AUTHOR,
                session_id=p.session_id,
                reason="Program lesson published after the Verifier's check.",
            )
            await db.commit()
        schedule_indexing(rt.memory, p.user_id)
    except Exception as exc:
        logger.warning("Lesson %s not stored in memory (%s)", p.lesson_id, type(exc).__name__)


async def finish(rt: LessonsRuntime, p: Published) -> bool:
    """The three follow-ups; returns "the lesson PDF is ready"."""
    try:
        await copy_resources(rt, p)
    except Exception as exc:
        logger.warning("Resources of lesson %s (%s)", p.lesson_id, type(exc).__name__)
    pdf_ok = await lesson_pdf(rt, p)
    await remember(rt, p)
    return pdf_ok

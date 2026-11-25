from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.brain.reading_repository import NoteReadingRepository

MAX_NOTES = 5
MAX_MATERIAL = 1_600
LESSON_REFERENCE = "tremplin:lesson:"


@dataclass(frozen=True)
class ActiveNote:
    item_id: str
    title: str
    version: str
    material: str


async def active_note_versions(
    db: AsyncSession, user_id: str, item_ids: Collection[str]
) -> dict[str, str]:
    return await NoteReadingRepository(db, user_id).versions(item_ids)


async def matching_notes(db: AsyncSession, user_id: str, terms: Sequence[str]) -> list[ActiveNote]:
    if not terms:
        return []
    found = await NoteReadingRepository(db, user_id).matching(terms, MAX_NOTES)
    return [
        ActiveNote(item_id, title, version, text[:MAX_MATERIAL])
        for item_id, title, version, text in found
    ]


@dataclass(frozen=True)
class ExplicitNote:
    lesson_id: str
    title: str
    markdown: str
    changed_at: datetime


async def explicitly_linked_lesson_notes(
    db: AsyncSession, user_id: str, lesson_ids: Collection[str]
) -> tuple[ExplicitNote, ...]:
    """Synced Markdown notes that name a lesson precisely."""
    references = {f"{LESSON_REFERENCE}{lesson_id}": lesson_id for lesson_id in lesson_ids}
    rows = await NoteReadingRepository(db, user_id).explicitly_linked(references.keys())
    return tuple(
        ExplicitNote(references[reference], title, markdown, changed_at)
        for reference, title, markdown, changed_at in rows
    )

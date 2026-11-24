"""Snapshot of the program, published lessons and explicitly linked notes."""

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.book.service.models import BookChapter, BookNote, BookSource, GlossaryEntry
from app.features.brain.service.reading import explicitly_linked_lesson_notes
from app.features.lessons.service.lessons import published_chapters
from app.features.program.service.chapters import ProgramOutline, program_outline
from app.features.program.service.programs import Loaded, load


def _module_ranks(loaded: Loaded, outline: ProgramOutline) -> dict[str, int]:
    """Chapters without a historical rank follow the order of weeks and modules."""
    ranks: dict[str, int] = {}
    taken: set[int] = set()
    for module in loaded.modules:
        index = outline.chapter_indices.get(module.id, -1)
        if not module.skipped and 0 <= index < len(outline.chapters) and index + 1 not in taken:
            ranks[module.id] = index + 1
            taken.add(index + 1)
    next_rank = len(outline.chapters) + 1 if ranks else 1
    for module in loaded.modules:
        if not module.skipped and module.id not in ranks:
            ranks[module.id] = next_rank
            next_rank += 1
    return ranks


def _terms(outline: ProgramOutline, module_id: str) -> tuple[str, ...]:
    index = outline.chapter_indices.get(module_id, -1)
    if not 0 <= index < len(outline.chapters):
        return ()
    chapter = outline.chapters[index]
    return (*chapter.requires, *(notion.name for notion in chapter.introduces))


async def book_source(db: AsyncSession, user_id: str, program_id: str) -> BookSource:
    loaded = await load(db, user_id, program_id)
    outline = await program_outline(db, user_id, program_id)
    ranks = _module_ranks(loaded, outline)
    rows = tuple(
        row for row in await published_chapters(db, user_id, program_id) if row.module_id in ranks
    )
    linked = await explicitly_linked_lesson_notes(db, user_id, {row.id for row in rows})
    notes: dict[str, list[BookNote]] = defaultdict(list)
    for note in linked:
        notes[note.lesson_id].append(BookNote(note.title, note.markdown))
    chapters = [
        BookChapter(
            rank=ranks[row.module_id],
            title=row.title,
            markdown=row.markdown,
            terms=_terms(outline, row.module_id),
            notes=tuple(notes[row.id]),
        )
        for row in rows
    ]
    chapters.sort(key=lambda chapter: chapter.rank)
    glossary = tuple(
        GlossaryEntry(notion.name, notion.definition)
        for chapter in outline.chapters
        for notion in chapter.introduces
    )
    changed = max(
        (
            loaded.program.updated_at,
            *(row.published_at for row in rows),
            *(note.changed_at for note in linked),
        )
    )
    return BookSource(program_id, loaded.program.title, changed, tuple(chapters), glossary)


def source_hash(source: BookSource) -> str:
    data = asdict(source)
    data["modified_at"] = source.modified_at.isoformat()
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # Already published editions must be recompiled when their rendering changes.
    return hashlib.sha256(b"book-diagrams-v1\0" + serialized.encode()).hexdigest()

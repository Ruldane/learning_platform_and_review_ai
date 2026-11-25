"""Match the reading text with the concepts of validated programs."""

import re
from dataclasses import dataclass
from itertools import islice

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.lessons.service.lessons import ready_lesson_id
from app.features.program.service.chapters import ProgramOutline, validated_outlines
from app.features.reading_stack.schemas import ReadingAnnotation

MAX_ANNOTATIONS = 120


@dataclass(frozen=True)
class Notion:
    term: str
    definition: str
    chapter: str
    module_id: str | None


def _notions(outlines: list[ProgramOutline]) -> dict[str, Notion]:
    found: dict[str, Notion] = {}
    for outline in outlines:
        chapters = {index: module for module, index in outline.chapter_indices.items()}
        for index, chapter in enumerate(outline.chapters):
            for notion in chapter.introduces:
                key = notion.name.casefold()
                found.setdefault(
                    key, Notion(notion.name, notion.definition, chapter.title, chapters.get(index))
                )
    return found


def _offsets(text: str, notions: dict[str, Notion]) -> list[tuple[int, int, Notion]]:
    terms = sorted(
        (notion.term for notion in notions.values()), key=lambda name: (-len(name), name)
    )
    names = "|".join(re.escape(term) for term in terms)
    pattern = re.compile(rf"(?<!\w)(?:{names})(?!\w)", re.IGNORECASE)
    matches = []
    previous = offset = 0
    for match in islice(pattern.finditer(text), MAX_ANNOTATIONS):
        notion = notions.get(match.group().casefold())
        if notion is None:
            continue
        offset += len(text[previous : match.start()].encode("utf-16-le")) // 2
        end = offset + len(match.group().encode("utf-16-le")) // 2
        matches.append((offset, end, notion))
        previous, offset = match.end(), end
    return matches


async def annotations(db: AsyncSession, user_id: str, text: str) -> list[ReadingAnnotation]:
    if not text:
        return []
    notions = _notions(await validated_outlines(db, user_id))
    if not notions:
        return []
    spans = _offsets(text, notions)
    module_ids = dict.fromkeys(notion.module_id for _, _, notion in spans if notion.module_id)
    lessons = {module: await ready_lesson_id(db, user_id, module) for module in module_ids}
    return [
        ReadingAnnotation(
            start=start,
            end=end,
            term=notion.term,
            definition=notion.definition,
            chapter=notion.chapter,
            lesson_id=lessons.get(notion.module_id) if notion.module_id else None,
        )
        for start, end, notion in spans
    ]

import json
from hashlib import sha256

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.lesson_variants.formatting import prepare_formats
from app.features.lesson_variants.repository import LessonVariants
from app.features.lesson_variants.schemas import LessonVariantOut, LessonVariantSummary
from app.features.lessons.service.lessons import get_lesson


def _revision(title: str, markdown: str) -> str:
    source = json.dumps([title, markdown], ensure_ascii=False, separators=(",", ":"))
    return sha256(source.encode("utf-8")).hexdigest()


async def prepare(db: AsyncSession, user_id: str, lesson_id: str) -> LessonVariantOut:
    source = await get_lesson(db, user_id, lesson_id)
    if source.status != "ready" or not source.markdown.strip():
        raise AppError("lesson_not_published", "Choose a published lesson.", 409)
    revision = _revision(source.title, source.markdown)
    editions = LessonVariants(db, user_id)
    existing = await editions.for_revision(lesson_id, revision)
    if existing is not None:
        return LessonVariantOut.model_validate(existing)

    review_markdown, reading_steps = prepare_formats(source.markdown)
    try:
        async with db.begin_nested():
            row = await editions.add(
                lesson_id=lesson_id,
                lesson_title=source.title,
                revision=revision,
                source_markdown=source.markdown,
                review_markdown=review_markdown,
                reading_steps=reading_steps,
            )
    except IntegrityError:
        concurrent = await editions.for_revision(lesson_id, revision)
        if concurrent is None:
            raise
        row = concurrent
    return LessonVariantOut.model_validate(row)


async def read(db: AsyncSession, user_id: str, edition_id: str) -> LessonVariantOut:
    row = await LessonVariants(db, user_id).get(edition_id)
    if row is None:
        raise AppError("lesson_variant_not_found", "Edition not found.", 404)
    return LessonVariantOut.model_validate(row)


async def list_editions(db: AsyncSession, user_id: str) -> list[LessonVariantSummary]:
    rows = await LessonVariants(db, user_id).history()
    return [LessonVariantSummary.model_validate(row) for row in rows]

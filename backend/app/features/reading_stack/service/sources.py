from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domains import normalize_domain
from app.core.errors import AppError
from app.features.memory.service.upload import normalize_url
from app.features.reading_stack.repository import ReadingSources
from app.features.reading_stack.schemas import ReadingSourceIn, ReadingSourceOut
from app.features.reading_stack.service.schedule import MAX_SOURCES


def source_not_found() -> AppError:
    return AppError("reading_source_not_found", "Source de lecture introuvable.", 404)


def _source_value(body: ReadingSourceIn) -> str:
    if body.kind == "rss":
        return normalize_url(body.value)
    if body.kind == "site":
        try:
            return normalize_domain(body.value)
        except ValueError:
            raise AppError(
                "reading_site_invalid", "Saisis un nom de domaine valide.", 422
            ) from None
    if len(body.value) > 180:
        raise AppError("reading_topic_too_long", "Le sujet doit tenir en 180 caractères.", 422)
    return " ".join(body.value.split())


async def list_sources(db: AsyncSession, user_id: str) -> list[ReadingSourceOut]:
    rows = await ReadingSources(db, user_id).list()
    return [
        ReadingSourceOut.model_validate(row) for row in sorted(rows, key=lambda row: row.created_at)
    ]


async def add_source(db: AsyncSession, user_id: str, body: ReadingSourceIn) -> ReadingSourceOut:
    repo = ReadingSources(db, user_id)
    if len(await repo.list()) >= MAX_SOURCES:
        raise AppError(
            "reading_source_limit", f"Tu peux suivre {MAX_SOURCES} sources au plus.", 409
        )
    value = _source_value(body)
    try:
        async with db.begin_nested():
            row = await repo.add(kind=body.kind, label=body.label, value=value)
    except IntegrityError:
        raise AppError("reading_source_exists", "Cette source est déjà suivie.", 409) from None
    return ReadingSourceOut.model_validate(row)


async def set_active(
    db: AsyncSession, user_id: str, source_id: str, active: bool
) -> ReadingSourceOut:
    row = await ReadingSources(db, user_id).update(source_id, active=active)
    if row is None:
        raise source_not_found()
    return ReadingSourceOut.model_validate(row)


async def remove_source(db: AsyncSession, user_id: str, source_id: str) -> None:
    if not await ReadingSources(db, user_id).delete(source_id):
        raise source_not_found()

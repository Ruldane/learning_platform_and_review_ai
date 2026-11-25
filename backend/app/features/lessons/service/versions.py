"""Reading published versions and the revision guard for the watch."""

from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.creation import PrepareSession
from app.core.errors import AppError
from app.db.models.lessons import Lesson
from app.features.lessons.repository import LessonRepository
from app.features.lessons.service.lessons import lesson_not_found


def fingerprint(title: str, markdown: str) -> str:
    return sha256(f"{title}\0{markdown}".encode()).hexdigest()


@dataclass(frozen=True)
class PublishedVersion:
    id: str
    title: str
    markdown: str
    session_id: str | None

    @classmethod
    def of(cls, row: Lesson) -> "PublishedVersion":
        return cls(row.id, row.title, row.markdown, row.session_id)

    @property
    def digest(self) -> str:
        return fingerprint(self.title, self.markdown)


@dataclass(frozen=True)
class RevisionGuard:
    digest: str
    prepare: PrepareSession

    def check(self, row: Lesson) -> None:
        if fingerprint(row.title, row.markdown) != self.digest:
            raise AppError(
                "lesson_update_stale", "The published lesson has changed since this proposal.", 409
            )


async def published_version(db: AsyncSession, user_id: str, lesson_id: str) -> PublishedVersion:
    row = await LessonRepository(db, user_id).get_fresh(lesson_id)
    if row is None:
        raise lesson_not_found()
    if row.status != "ready":
        raise AppError("lesson_not_ready", "This lesson is not ready yet.", 409)
    return PublishedVersion.of(row)


async def update_targets(
    db: AsyncSession, user_id: str, libraries: list[str]
) -> list[PublishedVersion]:
    return [
        PublishedVersion.of(row)
        for row in await LessonRepository(db, user_id).update_targets(libraries)
    ]

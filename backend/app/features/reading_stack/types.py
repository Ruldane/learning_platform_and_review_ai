from dataclasses import dataclass

from app.db.models.reading_stack import ReadingKind


@dataclass(frozen=True)
class CollectedItem:
    kind: ReadingKind
    url: str
    title: str
    summary: str
    text: str
    reason: str
    company: str | None = None

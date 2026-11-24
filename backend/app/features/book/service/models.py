"""Snapshot owned by an account, assembled before rendering."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BookNote:
    title: str
    markdown: str


@dataclass(frozen=True)
class GlossaryEntry:
    term: str
    definition: str


@dataclass(frozen=True)
class BookChapter:
    """Published chapter. Its rank (from 1) comes from the Strategist's table of contents."""

    rank: int
    title: str
    markdown: str
    terms: tuple[str, ...] = ()
    notes: tuple[BookNote, ...] = ()


@dataclass(frozen=True)
class BookSource:
    """Notes and chapters read for the same account, independently of the database."""

    program_id: str
    title: str
    modified_at: datetime
    chapters: tuple[BookChapter, ...]
    glossary: tuple[GlossaryEntry, ...] = ()
    language: str = "fr"

    def __post_init__(self) -> None:
        ranks = {chapter.rank for chapter in self.chapters}
        if len(ranks) != len(self.chapters) or any(rank < 1 for rank in ranks):
            raise ValueError("Invalid chapter ranks.")
        if self.modified_at.utcoffset() is None:
            raise ValueError("Edition date without a time zone.")

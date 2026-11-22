"""Instantané détenu par un compte, assemblé avant le rendu."""

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
    """Chapitre publié. Son rang (à partir de 1) vient du sommaire du Stratège."""

    rank: int
    title: str
    markdown: str
    terms: tuple[str, ...] = ()
    notes: tuple[BookNote, ...] = ()


@dataclass(frozen=True)
class BookSource:
    """Les notes et chapitres lus pour le même compte, indépendamment de la base."""

    program_id: str
    title: str
    modified_at: datetime
    chapters: tuple[BookChapter, ...]
    glossary: tuple[GlossaryEntry, ...] = ()
    language: str = "fr"

    def __post_init__(self) -> None:
        ranks = {chapter.rank for chapter in self.chapters}
        if len(ranks) != len(self.chapters) or any(rank < 1 for rank in ranks):
            raise ValueError("Rangs des chapitres invalides.")
        if self.modified_at.utcoffset() is None:
            raise ValueError("Date d'édition sans fuseau horaire.")

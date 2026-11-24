"""Shared PDF and EPUB preparation from the sanitised lesson Markdown."""

import re
from dataclasses import dataclass
from xml.etree.ElementTree import Element, fromstring

from app.core.lesson_structure import EXERCISE, SOLUTION, reading_section
from app.core.skills import normalize_skill_name
from app.features.book.service.models import BookChapter, BookSource, GlossaryEntry
from app.features.lessons.service.markdown import markdown_to_html

_VOID = re.compile(r"(<(?:br|hr))>")
_INVALID_XML = re.compile(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]")
_HEADINGS = {"h1", "h2", "h3", "h4"}


def xml_text(text: str) -> str:
    return _INVALID_XML.sub("", text)


@dataclass(frozen=True)
class PreparedNote:
    title: str
    body: tuple[Element, ...]


@dataclass(frozen=True)
class PreparedChapter:
    rank: int
    title: str
    body: tuple[Element, ...]
    exercises: tuple[Element, ...]
    notes: tuple[PreparedNote, ...]
    terms: tuple[str, ...]

    @property
    def anchor(self) -> str:
        return f"chapter-{self.rank}"

    @property
    def label(self) -> str:
        return f"{self.rank}. {self.title}"


@dataclass(frozen=True)
class IndexEntry:
    term: str
    chapters: tuple[PreparedChapter, ...]


@dataclass(frozen=True)
class PreparedBook:
    source: BookSource
    chapters: tuple[PreparedChapter, ...]
    glossary: tuple[GlossaryEntry, ...]
    index: tuple[IndexEntry, ...]


def _fragment(markdown: str, prefix: str, heading_shift: int) -> Element:
    # Lesson rendering strips raw HTML, scripts, images and relative links. Normalisation
    # only converts the empty tags and HTML entities it produces.
    safe = markdown_to_html(markdown, drop_title=True).html
    xhtml = _VOID.sub(r"\1 />", xml_text(safe)).replace("&nbsp;", "&#160;")
    root = fromstring(f"<div>{xhtml}</div>")
    for element in root.iter():
        if element.tag in _HEADINGS:
            element.tag = f"h{min(6, int(element.tag[1]) + heading_shift)}"
        if anchor := element.get("id"):
            element.set("id", f"{prefix}-{anchor}")
    return root


def _is_exercise(element: Element) -> bool:
    if element.tag != "section" or (heading := element.find("h3")) is None:
        return False
    return reading_section("".join(heading.itertext())) in {EXERCISE, SOLUTION}


def _prepare_chapter(chapter: BookChapter) -> PreparedChapter:
    prefix = f"chapter-{chapter.rank}"
    body: list[Element] = []
    exercises: list[Element] = []
    for section in _fragment(chapter.markdown, prefix, heading_shift=1):
        (exercises if _is_exercise(section) else body).append(section)
    notes = tuple(
        PreparedNote(note.title, tuple(_fragment(note.markdown, f"{prefix}-note-{n}", 3)))
        for n, note in enumerate(chapter.notes, start=1)
    )
    return PreparedChapter(
        chapter.rank, chapter.title, tuple(body), tuple(exercises), notes, chapter.terms
    )


def _glossary(entries: tuple[GlossaryEntry, ...]) -> dict[str, GlossaryEntry]:
    by_term: dict[str, GlossaryEntry] = {}
    for entry in entries:
        if key := normalize_skill_name(entry.term):
            by_term.setdefault(key, entry)
    return dict(sorted(by_term.items()))


def _index(
    chapters: tuple[PreparedChapter, ...], glossary: dict[str, GlossaryEntry]
) -> tuple[IndexEntry, ...]:
    labels = {key: entry.term for key, entry in glossary.items()}
    references: dict[str, list[PreparedChapter]] = {}
    for chapter in chapters:
        seen: set[str] = set()
        for term in chapter.terms or (chapter.title,):
            key = normalize_skill_name(term)
            if key and key not in seen:
                seen.add(key)
                labels.setdefault(key, term)
                references.setdefault(key, []).append(chapter)
    return tuple(IndexEntry(labels[key], tuple(references[key])) for key in sorted(references))


def prepare_book(source: BookSource) -> PreparedBook:
    ordered = sorted(source.chapters, key=lambda chapter: chapter.rank)
    chapters = tuple(_prepare_chapter(chapter) for chapter in ordered)
    glossary = _glossary(source.glossary)
    return PreparedBook(source, chapters, tuple(glossary.values()), _index(chapters, glossary))

"""Extract objectives, core sections, exercises and sources for guided study (D102, D103).
Preserve the headings in saved lessons. Use the first nonempty occurrence of each section."""

import re
from dataclasses import dataclass

from app.core.lesson_structure import (
    COMMON_MISTAKES,
    DIAGRAMS,
    EXERCISE,
    EXPLANATION,
    KEY_POINTS,
    OBJECTIVES,
    SOLUTION,
    SOURCES,
    WORKED_EXAMPLE,
    reading_section,
)

TAUGHT = (KEY_POINTS, EXPLANATION, DIAGRAMS, WORKED_EXAMPLE, COMMON_MISTAKES)

_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_H2 = re.compile(r"^\s{0,3}##(?!#)\s*(.*?)\s*#*\s*$")
_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_SOURCE = re.compile(
    r"^\s{0,3}(\d+)[.)]\s+(?:\[(?P<title>[^\]]+)\]\((?P<url>[^)\s]+)\)|(?P<plain>.*\S))"
)


@dataclass(frozen=True)
class LessonParts:
    objectives: list[str]
    sections: list[tuple[str, str]]
    exercise: str
    solution: str


def _chunks(markdown: str) -> list[tuple[str, str]]:
    """`(title, body)` of each top-level `##` section, in document order."""
    chunks: list[tuple[str, list[str]]] = []
    fence: str | None = None
    for line in markdown.splitlines():
        opened = _FENCE.match(line)
        if fence is not None:
            if opened and opened.group(1)[0] == fence[0] and len(opened.group(1)) >= len(fence):
                fence = None
        elif opened:
            fence = opened.group(1)
        elif (heading := _H2.match(line)) is not None:
            chunks.append((heading.group(1).strip(), []))
            continue
        if chunks:
            chunks[-1][1].append(line)
    return [(title, "\n".join(body).strip()) for title, body in chunks]


def _first(chunks: list[tuple[str, str]], section: str) -> tuple[str, str] | None:
    return next(
        ((title, body) for title, body in chunks if reading_section(title) == section and body),
        None,
    )


def lesson_parts(markdown: str) -> LessonParts:
    chunks = _chunks(markdown)
    sections = [found for section in TAUGHT if (found := _first(chunks, section)) is not None]
    objectives_body = (_first(chunks, OBJECTIVES) or ("", ""))[1]
    objectives = [
        item.group(1) for line in objectives_body.splitlines() if (item := _ITEM.match(line))
    ]
    return LessonParts(
        objectives=objectives,
        sections=sections,
        exercise=(_first(chunks, EXERCISE) or ("", ""))[1],
        solution=(_first(chunks, SOLUTION) or ("", ""))[1],
    )


def lesson_sources(markdown: str) -> list[tuple[int, str, str | None]]:
    """`(number, title, address)` of the « Sources » section (`n. [title](address)`), in
    number order; a duplicated number keeps the first line."""
    body = (_first(_chunks(markdown), SOURCES) or ("", ""))[1]
    found: dict[int, tuple[str, str | None]] = {}
    for line in body.splitlines():
        match = _SOURCE.match(line)
        if match is None:
            continue
        title = (match.group("title") or match.group("plain") or "").strip()
        url = match.group("url")
        found.setdefault(int(match.group(1)), (title, url))
    return [(number, *found[number]) for number in sorted(found)]

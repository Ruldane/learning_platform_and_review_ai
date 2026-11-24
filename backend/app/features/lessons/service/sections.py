"""Splitting a lesson (SPEC 3.5) for the Tutor's guided session (D102, D103): objectives, the
five core sections (L'essentiel, Explication, Schémas, Exemple travaillé, Erreurs fréquentes, in
that order), the exercise, its solution and the numbered sources.

Headings are recognized on top-level `##`, ignoring case, accents and curly apostrophe (the
Writer writes the `SECTIONS` headings in French, D90); a `##` inside a code block does not open
a section. A missing or empty section is omitted; when duplicated, the first one counts. Pure
functions, no database."""

import re
import unicodedata
from dataclasses import dataclass

# Folded prefixes of the taught sections, in session order.
TAUGHT = ("l'essentiel", "explication", "schema", "exemple travaille", "erreurs frequentes")
OBJECTIVES = "objectifs"
EXERCISE = "exercice"
SOLUTION = "corrige"
SOURCES = "sources"

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


def _folded(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.replace("’", "'"))
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(plain.split()).rstrip(" :").casefold()


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


def _first(chunks: list[tuple[str, str]], prefix: str) -> tuple[str, str] | None:
    return next(
        ((title, body) for title, body in chunks if _folded(title).startswith(prefix) and body),
        None,
    )


def lesson_parts(markdown: str) -> LessonParts:
    chunks = _chunks(markdown)
    sections = [found for prefix in TAUGHT if (found := _first(chunks, prefix)) is not None]
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

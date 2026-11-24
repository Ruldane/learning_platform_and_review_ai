"""Check new lessons against the English section structure and source rules (SPEC 3.5, D90)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.agents.nodes.lesson_reference import source_url_key
from app.agents.nodes.mermaid_rules import mermaid_problems, normalize_mermaid
from app.agents.nodes.verifier.code_language import python_language_problems
from app.agents.nodes.verifier.overlap import (
    MAX_QUOTE_WORDS,
    build_index,
    copied_from,
    split_quotes,
)
from app.core.lesson_structure import (
    DIAGRAMS,
    KEY_POINTS,
    LEGACY_SECTIONS,
    OBJECTIVES,
    SELF_ASSESSMENT,
)
from app.core.lesson_structure import SECTIONS as SECTIONS

MIN_WORDS = 1200
MAX_WORDS = 2500
MAX_OBJECTIVES = 3
ESSENTIAL_LINES = 5
SELF_TEST_QUESTIONS = 5

# Le parseur du rendu (`lessons.service.markdown`, `html: True`) : le Vérificateur voit la leçon
# comme le PDF la verra, HTML brut compris (D97).
_MD = MarkdownIt("commonmark", {"html": True}).enable("table")
_RAW_HTML_SHOWN = 40
_BARE_URL = re.compile(r"https?://[^\s<>\"')\]]+")
_MARKER = re.compile(r"\[(\d+)\]")
_TRAILING = ".,;:!?"


@dataclass(frozen=True)
class LessonCheck:
    words: int
    problems: list[str]
    categories: tuple[str, ...] = ()


@dataclass
class _Parsed:
    """Ce que les contrôles lisent dans le Markdown, en un seul parcours des jetons."""

    h1: list[str]
    h2: list[str]
    items: dict[str, int]  # éléments de liste de premier niveau, par section (clé repliée)
    mermaid: list[tuple[str, str]]
    texts: list[str]  # texte courant de chaque bloc (code exclu)
    links: list[str]
    raw_html: list[str]  # HTML brut hors des blocs de code (`html_block`, `html_inline`)
    code_problems: list[str]


def _key(text: str) -> str:
    return " ".join(text.replace("’", "'").split()).rstrip(":").casefold()


_LEGACY_HEADINGS = {
    _key(old): new for old, new in zip(LEGACY_SECTIONS, SECTIONS, strict=True) if old != new
}


def _inline_text(token: Token) -> str:
    parts: list[str] = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)


def _inline_links(token: Token) -> list[str]:
    links = [str(c.attrGet("href") or "") for c in token.children or [] if c.type == "link_open"]
    texts = "".join(c.content for c in token.children or [] if c.type == "text")
    links += [m.group(0).rstrip(_TRAILING) for m in _BARE_URL.finditer(texts)]
    return links


def _parse(markdown: str, *, show_input: bool = True, allow_legacy: bool = False) -> _Parsed:
    parsed = _Parsed([], [], {}, [], [], [], [], [])
    section = ""
    tokens = _MD.parse(markdown)
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0 and token.tag in ("h1", "h2"):
            title = " ".join(_inline_text(tokens[index + 1]).split())
            if token.tag == "h2" and allow_legacy:
                title = _LEGACY_HEADINGS.get(_key(title), title)
            (parsed.h1 if token.tag == "h1" else parsed.h2).append(title)
            if token.tag == "h2":
                section = _key(title)
        elif token.type == "list_item_open" and token.level == 1:
            parsed.items[section] = parsed.items.get(section, 0) + 1
        elif token.type == "fence":
            language = token.info.strip().lower()
            if language == "mermaid":
                parsed.mermaid.append((section, token.content))
            elif language in {"python", "py", "python3"} and token.map:
                parsed.code_problems.extend(
                    python_language_problems(token.content, token.map[0] + 2, show_input=show_input)
                )
        elif token.type == "html_block":
            parsed.raw_html.append(token.content)
        elif token.type == "inline":
            parsed.texts.append(_inline_text(token))
            parsed.links += _inline_links(token)
            kids = token.children or []
            parsed.raw_html += [c.content for c in kids if c.type == "html_inline"]
    return parsed


def _structure(parsed: _Parsed, title: str, *, show_input: bool) -> list[str]:
    problems: list[str] = []
    if not parsed.h1 or _key(parsed.h1[0]) != _key(title):
        label = f'"# {title}"' if show_input else "the expected main heading"
        problems.append(f"Start the lesson with {label}.")
    expected = [_key(s) for s in SECTIONS]
    found = [_key(h) for h in parsed.h2]
    for name, key in zip(SECTIONS, expected, strict=True):
        if key not in found:
            problems.append(f'Missing section "## {name}".')
    extra = [h for h, key in zip(parsed.h2, found, strict=True) if key not in expected]
    if show_input:
        problems += [f'Unexpected section "## {h}". Use the prescribed headings.' for h in extra]
    elif extra:
        problems.append(f"Unexpected sections: {len(extra)}. Use the prescribed headings.")
    present = [key for key in found if key in expected]
    if present != [key for key in expected if key in present]:
        problems.append("The sections are out of order. Follow the prescribed order.")
    return problems


def _counts(parsed: _Parsed) -> list[str]:
    problems: list[str] = []
    objectives = parsed.items.get(_key(OBJECTIVES), 0)
    if objectives > MAX_OBJECTIVES:
        problems.append(f"The lesson has {objectives} objectives. Use at most {MAX_OBJECTIVES}.")
    essential = parsed.items.get(_key(KEY_POINTS), 0)
    if essential != ESSENTIAL_LINES:
        problems.append(f'"{KEY_POINTS}" has {essential} bullets. Use exactly {ESSENTIAL_LINES}.')
    questions = parsed.items.get(_key(SELF_ASSESSMENT), 0)
    if questions != SELF_TEST_QUESTIONS:
        problems.append(
            f"Self-assessment has {questions} questions. Use exactly {SELF_TEST_QUESTIONS}."
        )
    return problems


def _diagrams(parsed: _Parsed, *, show_input: bool) -> list[str]:
    if not any(section == _key(DIAGRAMS) for section, _ in parsed.mermaid):
        return [f'Add at least one Mermaid flowchart in "{DIAGRAMS}".']
    problems: list[str] = []
    for number, (_, code) in enumerate(parsed.mermaid, start=1):
        try:
            normalize_mermaid(code)
        except ValueError:
            first = (
                (mermaid_problems(code) or ["forme non admise"])[0]
                if show_input
                else ("utilise un schéma `flowchart` conforme.")
            )
            problems.append(f"Schéma Mermaid {number} refusé : {first}")
    return problems


def _raw_html(parsed: _Parsed, *, show_input: bool) -> list[str]:
    """Le rendu retire une balise en ligne et montre un bloc HTML en texte brut (D97) : la leçon
    n'en contient donc aucun hors du code."""
    if not parsed.raw_html:
        return []
    sample = " ".join(parsed.raw_html[0].split())[:_RAW_HTML_SHOWN]
    first = f", dont « {sample} »" if show_input else ""
    return [
        f"HTML brut hors d'un bloc de code ({len(parsed.raw_html)} fois{first}) : "
        "mets toute balise entre accents graves, par exemple `<pre>`, ou dans un bloc de code."
    ]


def _length(words: int) -> list[str]:
    if MIN_WORDS <= words <= MAX_WORDS:
        return []
    return [f"La leçon fait {words} mots : il en faut entre 1 200 et 2 500 (blocs de code exclus)."]


def _references(parsed: _Parsed, sources: Sequence[tuple[int, str, str]]) -> list[str]:
    problems: list[str] = []
    known_urls = {k for _n, url, _t in sources if (k := source_url_key(url)) is not None}
    for link in dict.fromkeys(parsed.links):
        if source_url_key(link) not in known_urls:
            problems.append(f"Lien absent des sources lues : {link}")
    numbers = {number for number, _url, _text in sources}
    unknown = sorted(
        {int(m.group(1)) for text in parsed.texts for m in _MARKER.finditer(text)} - numbers
    )
    problems += [f"Marqueur [{n}] inconnu : aucune source n'a ce numéro." for n in unknown]
    return problems


def _quotes_and_copies(parsed: _Parsed, sources: Sequence[tuple[int, str, str]]) -> list[str]:
    problems: list[str] = []
    outside: list[str] = []
    for text in parsed.texts:
        parts, quotes = split_quotes(text)
        outside += parts
        problems += [
            f"Citation de plus de {MAX_QUOTE_WORDS} mots : une citation est courte."
            for quote in quotes
            if len(quote.split()) > MAX_QUOTE_WORDS
        ]
    for number in sorted(copied_from(outside, build_index(sources))):
        problems.append(
            f"Passage de plus de {MAX_QUOTE_WORDS} mots recopié de la source [{number}] : "
            f"reformule-le, ou cite-le court entre « » suivi de [{number}]."
        )
    return list(dict.fromkeys(problems))


def check_lesson(
    markdown: str,
    *,
    title: str,
    sources: Sequence[tuple[int, str, str]],
    allow_legacy: bool = False,
) -> LessonCheck:
    """`sources` : `(numéro, adresse, texte lu)` des seules sources admises dans la leçon."""
    parsed = _parse(markdown, allow_legacy=allow_legacy)
    words, groups = _offline_checks(parsed, title, show_input=True)
    groups.extend(
        (
            ("Références aux sources", _references(parsed, sources)),
            ("Citations et reformulation", _quotes_and_copies(parsed, sources)),
        )
    )
    return LessonCheck(
        words=words,
        problems=[problem for _, problems in groups for problem in problems],
        categories=tuple(label for label, problems in groups if problems),
    )


def _offline_checks(
    parsed: _Parsed,
    title: str,
    *,
    show_input: bool,
) -> tuple[int, list[tuple[str, list[str]]]]:
    words = sum(len(text.split()) for text in parsed.texts)
    return words, [
        ("Structure du chapitre", _structure(parsed, title, show_input=show_input)),
        ("HTML dans le texte", _raw_html(parsed, show_input=show_input)),
        ("Listes d’objectifs et de questions", _counts(parsed)),
        ("Schémas Mermaid", _diagrams(parsed, show_input=show_input)),
        ("Anglais dans les exemples Python", parsed.code_problems),
        ("Longueur du chapitre", _length(words)),
    ]


def check_submission(
    markdown: str, *, title: str, allow_legacy: bool = False
) -> tuple[list[str], list[str]]:
    """Contrôles possibles avant la lecture des sources, sans citer l'entrée dans les refus."""
    parsed = _parse(markdown, show_input=False, allow_legacy=allow_legacy)
    _, groups = _offline_checks(parsed, title, show_input=False)
    problems = [problem for _, messages in groups for problem in messages]
    return [*problems, *_quotes_and_copies(parsed, ())], list(dict.fromkeys(parsed.links))


def has_legacy_headings(markdown: str) -> bool:
    return any(_key(title) in _LEGACY_HEADINGS for title in _parse(markdown).h2)


def change_heading(markdown: str, title: str) -> str:
    """Réécrit l'en-tête du chapitre quand seul le titre est retouché."""
    for token in _MD.parse(markdown):
        if token.type == "heading_open" and token.tag == "h1" and token.level == 0 and token.map:
            start, end = token.map
            lines = markdown.splitlines(keepends=True)
            return "".join([*lines[:start], f"# {title}\n", *lines[end:]])
    return markdown

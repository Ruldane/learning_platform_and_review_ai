"""Contrôles déterministes d'une leçon (SPEC 3.5, D90) : structure en 11 sections, nombres
d'éléments, schéma Mermaid, longueur, liens et marqueurs `[n]` connus des sources lues, absence
de recopie. Le Vérificateur y ajoute le contrôle des faits (`verify`).

Les titres de section sont toujours ceux de `SECTIONS`, en français, quelle que soit la langue de
la leçon : le rendu HTML/PDF (D89) reconnaît ses encadrés sur ces titres."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.agents.nodes.mermaid_rules import mermaid_problems, normalize_mermaid
from app.agents.nodes.verifier.overlap import (
    MAX_QUOTE_WORDS,
    build_index,
    copied_from,
    split_quotes,
)

SECTIONS = (
    "Objectifs",
    "Prérequis",
    "L'essentiel en 5 lignes",
    "Explication",
    "Schémas",
    "Exemple travaillé",
    "Erreurs fréquentes",
    "Exercice",
    "Corrigé de l'exercice",
    "Sources",
    "Auto-évaluation",
)
MIN_WORDS = 1200
MAX_WORDS = 2500
MAX_OBJECTIVES = 3
ESSENTIAL_LINES = 5
SELF_TEST_QUESTIONS = 5

_MD = MarkdownIt("commonmark", {"html": False}).enable("table")
_BARE_URL = re.compile(r"https?://[^\s<>\"')\]]+")
_MARKER = re.compile(r"\[(\d+)\]")
_TRAILING = ".,;:!?"


@dataclass(frozen=True)
class LessonCheck:
    words: int
    problems: list[str]


@dataclass
class _Parsed:
    """Ce que les contrôles lisent dans le Markdown, en un seul parcours des jetons."""

    h1: list[str]
    h2: list[str]
    items: dict[str, int]  # éléments de liste de premier niveau, par section (clé repliée)
    mermaid: list[str]
    texts: list[str]  # texte courant de chaque bloc (code exclu)
    links: list[str]


def _key(text: str) -> str:
    return " ".join(text.replace("’", "'").split()).rstrip(":").casefold()


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


def _parse(markdown: str) -> _Parsed:
    parsed = _Parsed([], [], {}, [], [], [])
    section = ""
    tokens = _MD.parse(markdown)
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0 and token.tag in ("h1", "h2"):
            title = " ".join(_inline_text(tokens[index + 1]).split())
            (parsed.h1 if token.tag == "h1" else parsed.h2).append(title)
            if token.tag == "h2":
                section = _key(title)
        elif token.type == "list_item_open" and token.level == 1:
            parsed.items[section] = parsed.items.get(section, 0) + 1
        elif token.type == "fence" and token.info.strip().lower() == "mermaid":
            parsed.mermaid.append(token.content)
        elif token.type == "inline":
            parsed.texts.append(_inline_text(token))
            parsed.links += _inline_links(token)
    return parsed


def _url_key(url: str) -> str | None:
    """Clé tolérante d'une adresse : hôte en minuscules, sans `/` final ni fragment."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _structure(parsed: _Parsed, title: str) -> list[str]:
    problems: list[str] = []
    if not parsed.h1 or _key(parsed.h1[0]) != _key(title):
        problems.append(f"Titre « # {title} » absent : la leçon commence par ce titre exact.")
    expected = [_key(s) for s in SECTIONS]
    found = [_key(h) for h in parsed.h2]
    for name, key in zip(SECTIONS, expected, strict=True):
        if key not in found:
            problems.append(f"Section manquante : « ## {name} ».")
    extra = [h for h, key in zip(parsed.h2, found, strict=True) if key not in expected]
    problems += [f"Section en trop : « ## {h} » (la structure est fixe)." for h in extra]
    present = [key for key in found if key in expected]
    if present != [key for key in expected if key in present]:
        problems.append("Sections dans le désordre : respecte l'ordre de la structure fixe.")
    return problems


def _counts(parsed: _Parsed) -> list[str]:
    problems: list[str] = []
    objectives = parsed.items.get(_key("Objectifs"), 0)
    if objectives > MAX_OBJECTIVES:
        problems.append(f"{objectives} objectifs : {MAX_OBJECTIVES} objectifs au plus.")
    essential = parsed.items.get(_key("L'essentiel en 5 lignes"), 0)
    if essential != ESSENTIAL_LINES:
        problems.append(
            f"« L'essentiel en 5 lignes » compte {essential} puce(s) : il en faut exactement "
            f"{ESSENTIAL_LINES}."
        )
    questions = parsed.items.get(_key("Auto-évaluation"), 0)
    if questions != SELF_TEST_QUESTIONS:
        problems.append(
            f"L'auto-évaluation compte {questions} question(s) : il en faut exactement "
            f"{SELF_TEST_QUESTIONS}."
        )
    return problems


def _diagrams(parsed: _Parsed) -> list[str]:
    if not parsed.mermaid:
        return ["Aucun schéma : au moins un bloc ```mermaid (flowchart) dans « Schémas »."]
    problems: list[str] = []
    for number, code in enumerate(parsed.mermaid, start=1):
        try:
            normalize_mermaid(code)
        except ValueError:
            first = (mermaid_problems(code) or ["forme non admise"])[0]
            problems.append(f"Schéma Mermaid {number} refusé : {first}")
    return problems


def _length(words: int) -> list[str]:
    if MIN_WORDS <= words <= MAX_WORDS:
        return []
    return [f"La leçon fait {words} mots : il en faut entre 1 200 et 2 500 (blocs de code exclus)."]


def _references(parsed: _Parsed, sources: Sequence[tuple[int, str, str]]) -> list[str]:
    problems: list[str] = []
    known_urls = {k for _n, url, _t in sources if (k := _url_key(url)) is not None}
    for link in dict.fromkeys(parsed.links):
        if _url_key(link) not in known_urls:
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
    markdown: str, *, title: str, sources: Sequence[tuple[int, str, str]]
) -> LessonCheck:
    """`sources` : `(numéro, adresse, texte lu)` des seules sources admises dans la leçon."""
    parsed = _parse(markdown)
    words = sum(len(text.split()) for text in parsed.texts)
    problems = [
        *_structure(parsed, title),
        *_counts(parsed),
        *_diagrams(parsed),
        *_length(words),
        *_references(parsed, sources),
        *_quotes_and_copies(parsed, sources),
    ]
    return LessonCheck(words=words, problems=problems)

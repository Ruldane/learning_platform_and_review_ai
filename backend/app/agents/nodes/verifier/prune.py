"""Périmètre du contrôle des faits et retrait déterministe des phrases non sourcées (D97 n° 11).

Le Vérificateur cite chaque affirmation non sourcée entre « » (coupes par « ... »). Le plus long
fragment cité, normalisé (casse, espaces, ponctuation, mise en forme), situe la phrase dans un
paragraphe de la leçon, donc dans sa section :
- `in_scope` écarte une affirmation qui n'est située que hors des sections de faits (objectifs,
  prérequis, exercice, corrigé, sources, auto-évaluation) : ce ne sont pas des faits sourçables ;
- `prune` retire les phrases qui portent les affirmations (l'élément de liste entier s'il n'en
  reste rien), sans appel au modèle : aucun fait nouveau ne peut entrer. Les titres, les blocs de
  code et les tableaux ne sont jamais touchés ; une affirmation qui n'y est pas située est
  comptée introuvable.

Pur : aucune écriture, aucun journal (le contenu de la leçon n'en sort jamais)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

IN_SCOPE = ("L'essentiel en 5 lignes", "Explication", "Exemple travaillé", "Erreurs fréquentes")
MIN_FRAGMENT_WORDS = 3  # en deçà, un fragment cité est trop ambigu pour situer une phrase

_MD = MarkdownIt("commonmark", {"html": True}).enable("table")  # le parseur du rendu (D97)
_QUOTED = re.compile(r"«([^»]*)»|“([^”]*)”|\"([^\"]*)\"")
_CUT = re.compile(r"\[?(?:\.\.\.|…)\]?")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_WORD = re.compile(r"\w+")
_SENTENCE_END = re.compile(r"[.!?…][*_»\"')]*(?=\s)")
_ITEM_PREFIX = re.compile(r"^\s*(?:>\s?)*(?:[-*+]|\d+[.)])\s+")
_LINE_PREFIX = re.compile(r"^\s*(?:>\s?)*")


@dataclass(frozen=True)
class Pruned:
    markdown: str
    removed: int  # phrases retirées
    unlocated: int  # affirmations introuvables dans les sections de faits


@dataclass(frozen=True)
class _Block:
    """Un paragraphe de la leçon, découpé en phrases."""

    section: str  # clé repliée de la section `##` qui le contient
    lines: tuple[int, int]  # ses lignes `[début, fin)`
    item: tuple[int, int] | None  # l'élément de liste dont il est le premier bloc
    prefix: str  # marque de liste ou de citation de sa première ligne
    sentences: list[str]
    words: list[tuple[str, int]]  # (mot normalisé, rang de sa phrase)


def _key(text: str) -> str:
    return " ".join(text.replace("’", "'").split()).rstrip(":").casefold()


_SCOPE = {_key(name) for name in IN_SCOPE}


def _words(text: str) -> list[str]:
    """Mots sans casse, ponctuation, adresses de liens ni mise en forme Markdown."""
    return _WORD.findall(_LINK_TARGET.sub("]", text).casefold())


def _sentences(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        parts.append(text[start : match.end()].strip())
        start = match.end()
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _block(
    lines: list[str], span: tuple[int, int], item: tuple[int, int] | None, section: str
) -> _Block:
    raw = lines[span[0] : span[1]]
    match = (_ITEM_PREFIX if item else _LINE_PREFIX).match(raw[0])
    prefix = match.group(0) if match else ""
    rest = [_LINE_PREFIX.sub("", line).strip() for line in raw[1:]]
    sentences = _sentences(" ".join([raw[0][len(prefix) :].strip(), *rest]))
    words = [(word, rank) for rank, sentence in enumerate(sentences) for word in _words(sentence)]
    return _Block(section, span, item, prefix, sentences, words)


def _span(token: Token) -> tuple[int, int] | None:
    return (token.map[0], token.map[1]) if token.map else None


def _blocks(markdown: str) -> list[_Block]:
    lines = markdown.split("\n")
    tokens = _MD.parse(markdown)
    blocks: list[_Block] = []
    section = ""
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0:
            section = _key(tokens[index + 1].content)
        elif token.type == "paragraph_open" and (span := _span(token)) is not None:
            before = tokens[index - 1] if index else None
            item = _span(before) if before and before.type == "list_item_open" else None
            blocks.append(_block(lines, span, item, section))
    return blocks


def fragment(claim: str) -> list[str] | None:
    """Mots du plus long fragment de la première citation de l'affirmation, ou `None`."""
    match = _QUOTED.search(claim)
    if match is None:
        return None
    quoted = next(group for group in match.groups() if group is not None)
    best = max((_words(part) for part in _CUT.split(quoted)), key=len)
    return best if len(best) >= MIN_FRAGMENT_WORDS else None


def _hits(blocks: list[_Block], claim: str) -> list[tuple[int, set[int]]]:
    """`(paragraphe, rangs des phrases)` de chaque endroit où le fragment cité apparaît."""
    words = fragment(claim)
    if words is None:
        return []
    size = len(words)
    hits: list[tuple[int, set[int]]] = []
    for number, block in enumerate(blocks):
        found = [w for w, _rank in block.words]
        for start in range(len(found) - size + 1):
            if found[start : start + size] == words:
                hits.append((number, {rank for _w, rank in block.words[start : start + size]}))
    return hits


def in_scope(markdown: str, claims: Sequence[str]) -> list[str]:
    """Les affirmations à juger : situées dans une section de faits, ou introuvables (le
    Rédacteur peut encore les corriger). Une affirmation située ailleurs seulement est écartée."""
    blocks = _blocks(markdown)
    kept: list[str] = []
    for claim in claims:
        hits = _hits(blocks, claim)
        if not hits or any(blocks[number].section in _SCOPE for number, _ranks in hits):
            kept.append(claim)
    return kept


def _edits(
    lines: list[str], blocks: list[_Block], doomed: dict[int, set[int]]
) -> list[tuple[int, int, list[str]]]:
    edits: list[tuple[int, int, list[str]]] = []
    for number, ranks in doomed.items():
        block = blocks[number]
        kept = [s for rank, s in enumerate(block.sentences) if rank not in ranks]
        if kept:
            edits.append((*block.lines, [block.prefix + " ".join(kept)]))
        elif block.item is None:
            edits.append((*block.lines, []))
        else:
            start, end = block.item
            while end > start + 1 and not lines[end - 1].strip():
                end -= 1  # la ligne vide qui suit l'élément reste : rien ne se recolle
            if end > block.lines[1]:  # l'élément porte d'autres blocs (du code) : il reste
                edits.append((*block.lines, [block.prefix.rstrip()]))
            else:
                edits.append((start, end, []))
    return edits


def prune(markdown: str, claims: Sequence[str]) -> Pruned:
    """La leçon sans les phrases qui portent `claims` (dans les sections de faits seulement)."""
    blocks = _blocks(markdown)
    doomed: dict[int, set[int]] = {}
    unlocated = 0
    for claim in claims:
        hits = [(n, r) for n, r in _hits(blocks, claim) if blocks[n].section in _SCOPE]
        unlocated += 0 if hits else 1
        for number, ranks in hits:
            doomed.setdefault(number, set()).update(ranks)
    lines = markdown.split("\n")
    last = len(lines) + 1
    for start, end, new in sorted(_edits(lines, blocks, doomed), reverse=True):
        if end > last:
            continue  # sécurité : jamais deux retraits sur les mêmes lignes
        lines[start:end] = new
        last = start
    return Pruned("\n".join(lines), sum(len(r) for r in doomed.values()), unlocated)

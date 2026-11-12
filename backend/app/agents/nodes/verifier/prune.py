"""Périmètre du contrôle des faits et retrait déterministe des phrases non sourcées (D97 n° 11).

Le Vérificateur cite chaque affirmation non sourcée entre « » (coupes par « ... »). Le plus long
fragment cité, normalisé (casse, espaces, ponctuation, mise en forme), situe la phrase dans un
paragraphe de la leçon, donc dans sa section. Il ne la situe que s'il n'apparaît que dans une
seule phrase, et, s'il est court, s'il en couvre l'essentiel : sinon il est introuvable.
- `in_scope` écarte une affirmation qui n'est située que hors des sections de faits (objectifs,
  prérequis, exercice, corrigé, sources, auto-évaluation) : ce ne sont pas des faits sourçables ;
- `prune` retire les phrases qui portent les affirmations (l'élément de liste entier, sous-liste
  comprise, s'il n'en reste rien), sans appel au modèle : aucun fait nouveau ne peut entrer. Les
  titres, les blocs de code et les tableaux ne sont jamais touchés ; une affirmation qui n'y est
  pas située, ou dont le retrait toucherait du code, est comptée introuvable ;
- `still_cited` compte les affirmations dont le fragment reste dans le texte après le retrait.

Pur : aucune écriture, aucun journal (le contenu de la leçon n'en sort jamais)."""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

IN_SCOPE = ("L'essentiel en 5 lignes", "Explication", "Exemple travaillé", "Erreurs fréquentes")
MIN_FRAGMENT_WORDS = 3  # en deçà, un fragment cité est trop ambigu pour situer une phrase
SHORT_FRAGMENT_WORDS = 6  # en deçà, le fragment doit couvrir l'essentiel de sa phrase
MIN_COVERAGE = 0.6

_MD = MarkdownIt("commonmark", {"html": True}).enable("table")  # le parseur du rendu (D97)
_QUOTED = re.compile(r"«([^»]*)»|“([^”]*)”|\"([^\"]*)\"")
_CUT = re.compile(r"\[?(?:\.\.\.|…)\]?")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_WORD = re.compile(r"\w+")
# Fin de phrase : ponctuation, fermeture de mise en forme, puis les marqueurs `[n]` qui la suivent.
_SENTENCE_END = re.compile(r"[.!?…][*_»\"')]*(?:\s*\[\d+\])*(?=\s)")
_ABBREVIATION = re.compile(
    r"(?:^|[\s(«\"'])(?:p\.\s?ex|etc|cf|env|m|e\.\s?g|i\.\s?e|c\.-à-d|ex|vs)\.$", re.IGNORECASE
)
_NEXT_LETTER = re.compile(r"\s*[*_`«\"'(\[]*(\S?)")
_ITEM_PREFIX = re.compile(r"^\s*(?:>\s?)*(?:[-*+]|\d+[.)])\s+")
_LINE_PREFIX = re.compile(r"^\s*(?:>\s?)*")

type Span = tuple[int, int]
type Hit = tuple[int, frozenset[int]]  # (paragraphe, rangs des phrases)


@dataclass(frozen=True)
class Pruned:
    markdown: str
    removed: int  # phrases retirées
    unlocated: int  # affirmations introuvables, ambiguës ou non retirables


@dataclass(frozen=True)
class _Block:
    """Un paragraphe de la leçon, découpé en phrases."""

    section: str  # clé repliée de la section `##` qui le contient
    lines: Span  # ses lignes `[début, fin)`
    item: Span | None  # l'élément de liste dont il est le premier bloc
    prefix: str  # marque de liste ou de citation de sa première ligne
    sentences: list[str]
    words: list[tuple[str, int]]  # (mot normalisé, rang de sa phrase)


def _key(text: str) -> str:
    return " ".join(text.replace("’", "'").split()).rstrip(":").casefold()


_SCOPE = {_key(name) for name in IN_SCOPE}


def _words(text: str) -> list[str]:
    """Mots sans casse, ponctuation, adresses de liens ni mise en forme Markdown."""
    return _WORD.findall(_LINK_TARGET.sub("]", text).casefold())


def _ends_sentence(text: str, match: re.Match[str]) -> bool:
    """Pas de coupe après une abréviation (« p. ex. », « etc. »…) ni devant une minuscule."""
    if text[match.start()] == "." and _ABBREVIATION.search(text[: match.start() + 1]):
        return False
    following = _NEXT_LETTER.match(text, match.end())
    letter = following.group(1) if following else ""
    return not letter.islower()


def _sentences(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        if _ends_sentence(text, match):
            parts.append(text[start : match.end()].strip())
            start = match.end()
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _block(lines: list[str], span: Span, item: Span | None, section: str) -> _Block:
    raw = lines[span[0] : span[1]]
    match = (_ITEM_PREFIX if item else _LINE_PREFIX).match(raw[0])
    prefix = match.group(0) if match else ""
    rest = [_LINE_PREFIX.sub("", line).strip() for line in raw[1:]]
    sentences = _sentences(" ".join([raw[0][len(prefix) :].strip(), *rest]))
    words = [(word, rank) for rank, sentence in enumerate(sentences) for word in _words(sentence)]
    return _Block(section, span, item, prefix, sentences, words)


def _span(token: Token) -> Span | None:
    return (token.map[0], token.map[1]) if token.map else None


def _parse(markdown: str) -> tuple[list[_Block], list[Span]]:
    """Les paragraphes de la leçon, et les lignes de ses blocs de code."""
    lines = markdown.split("\n")
    tokens = _MD.parse(markdown)
    blocks: list[_Block] = []
    code: list[Span] = []
    section = ""
    for index, token in enumerate(tokens):
        span = _span(token)
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0:
            section = _key(tokens[index + 1].content)
        elif token.type in ("fence", "code_block") and span is not None:
            code.append(span)
        elif token.type == "paragraph_open" and span is not None:
            before = tokens[index - 1] if index else None
            item = _span(before) if before and before.type == "list_item_open" else None
            blocks.append(_block(lines, span, item, section))
    return blocks, code


def fragment(claim: str) -> list[str] | None:
    """Mots du plus long fragment de la première citation de l'affirmation, ou `None`."""
    match = _QUOTED.search(claim)
    if match is None:
        return None
    quoted = next(group for group in match.groups() if group is not None)
    best = max((_words(part) for part in _CUT.split(quoted)), key=len)
    return best if len(best) >= MIN_FRAGMENT_WORDS else None


def _occurs(found: list[str], words: list[str]) -> list[int]:
    size = len(words)
    return [i for i in range(len(found) - size + 1) if found[i : i + size] == words]


def _locate(blocks: list[_Block], claim: str) -> Hit | None:
    """La seule phrase (ou suite de phrases) qui porte le fragment cité ; `None` s'il est absent,
    présent dans plusieurs phrases, ou trop court pour l'essentiel de la sienne."""
    words = fragment(claim)
    if words is None:
        return None
    hits: set[Hit] = set()
    for number, block in enumerate(blocks):
        found = [w for w, _rank in block.words]
        for start in _occurs(found, words):
            hits.add((number, frozenset(r for _w, r in block.words[start : start + len(words)])))
    if len(hits) != 1:
        return None
    number, ranks = hits.pop()
    total = sum(1 for _w, rank in blocks[number].words if rank in ranks)
    if len(words) < SHORT_FRAGMENT_WORDS and len(words) < MIN_COVERAGE * total:
        return None
    return number, ranks


def in_scope(markdown: str, claims: Sequence[str]) -> list[str]:
    """Les affirmations à juger : situées dans une section de faits, ou introuvables (le
    Rédacteur peut encore les corriger). Une affirmation située ailleurs seulement est écartée."""
    blocks, _code = _parse(markdown)
    kept: list[str] = []
    for claim in claims:
        hit = _locate(blocks, claim)
        if hit is None or blocks[hit[0]].section in _SCOPE:
            kept.append(claim)
    return kept


def _edit(
    block: _Block, ranks: set[int], lines: list[str], code: list[Span]
) -> tuple[int, int, list[str]] | None:
    """Le remplacement des lignes du paragraphe ; `None` s'il emporterait du code."""
    kept = [s for rank, s in enumerate(block.sentences) if rank not in ranks]
    if kept:
        return (*block.lines, [block.prefix + " ".join(kept)])
    if block.item is None:
        return (*block.lines, [])
    start, end = block.item
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1  # la ligne vide qui suit l'élément reste : rien ne se recolle
    if any(start <= a and b <= end for a, b in code):
        return None  # un bloc de code n'est jamais retiré
    return (start, end, [])  # l'élément entier, sous-liste comprise


def _apply(lines: list[str], edits: list[tuple[int, int, list[str]]]) -> str:
    """Applique les remplacements ; un remplacement contenu dans un autre (sous-élément d'un
    élément retiré) est déjà emporté. Deux remplacements qui se chevauchent sont une erreur."""
    outer: list[tuple[int, int, list[str]]] = []
    for edit in sorted(edits, key=lambda e: (e[0], -e[1])):
        if outer and edit[1] <= outer[-1][1]:
            continue
        if outer and edit[0] < outer[-1][1]:
            raise ValueError("Retraits qui se chevauchent dans la leçon.")
        outer.append(edit)
    for start, end, new in reversed(outer):
        lines[start:end] = new
    return "\n".join(lines)


def prune(markdown: str, claims: Sequence[str]) -> Pruned:
    """La leçon sans les phrases qui portent `claims` (dans les sections de faits seulement)."""
    blocks, code = _parse(markdown)
    doomed: dict[int, set[int]] = {}
    owners: Counter[int] = Counter()
    unlocated = 0
    for claim in claims:
        hit = _locate(blocks, claim)
        if hit is None or blocks[hit[0]].section not in _SCOPE:
            unlocated += 1
            continue
        doomed.setdefault(hit[0], set()).update(hit[1])
        owners[hit[0]] += 1
    lines = markdown.split("\n")
    edits: list[tuple[int, int, list[str]]] = []
    removed = 0
    for number, ranks in doomed.items():
        edit = _edit(blocks[number], ranks, lines, code)
        if edit is None:
            unlocated += owners[number]
        else:
            edits.append(edit)
            removed += len(ranks)
    return Pruned(_apply(lines, edits), removed, unlocated)


def still_cited(markdown: str, claims: Sequence[str]) -> int:
    """Affirmations dont le fragment cité figure encore dans le texte (paragraphes, tableaux,
    titres ; hors code) : contrôle après retrait."""
    texts = [_words(t.content) for t in _MD.parse(markdown) if t.type == "inline"]
    count = 0
    for claim in claims:
        words = fragment(claim)
        if words is not None and any(_occurs(found, words) for found in texts):
            count += 1
    return count

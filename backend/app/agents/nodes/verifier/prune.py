"""Scope of the fact check and deterministic removal of unsourced sentences (D97 no. 11).

The Verifier quotes each unsourced claim between « » (cuts marked by « ... »). The longest
quoted fragment, normalized (case, spaces, punctuation, formatting), locates the sentence in a
paragraph of the lesson, hence in its section. It only locates it if it appears in a single
sentence and, if it is short, if it covers most of it: otherwise it is not found.
- `in_scope` discards a claim that is only located outside the fact sections (objectives,
  prerequisites, exercise, solution, sources, self-assessment): these are not sourceable facts;
- `prune` removes the sentences that carry the claims (the whole list item, sub-list included,
  if nothing remains of it), without a model call: no new fact can come in. Headings, code blocks
  and tables are never touched; a claim that is not located there, or whose removal would touch
  code, is counted as not found;
- `still_cited` counts the claims whose fragment remains in the text after the removal.

Pure: no write, no log (the lesson content never leaves it)."""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.core.lesson_structure import (
    COMMON_MISTAKES,
    EXPLANATION,
    KEY_POINTS,
    WORKED_EXAMPLE,
    reading_section,
)

IN_SCOPE = (KEY_POINTS, EXPLANATION, WORKED_EXAMPLE, COMMON_MISTAKES)
_SCOPE = set(IN_SCOPE)
MIN_FRAGMENT_WORDS = 3  # below this, a quoted fragment is too ambiguous to locate a sentence
SHORT_FRAGMENT_WORDS = 6  # below this, the fragment must cover most of its sentence
MIN_COVERAGE = 0.6

_MD = MarkdownIt("commonmark", {"html": True}).enable("table")  # the renderer's parser (D97)
_QUOTED = re.compile(r"«([^»]*)»|“([^”]*)”|\"([^\"]*)\"")
_CUT = re.compile(r"\[?(?:\.\.\.|…)\]?")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_WORD = re.compile(r"\w+")
# End of sentence: punctuation, closing formatting, then the `[n]` markers that follow it.
_SENTENCE_END = re.compile(r"[.!?…][*_»\"')]*(?:\s*\[\d+\])*(?=\s)")
# Abbreviations: English ones (e.g., i.e., etc., vs.) and French ones (p. ex., c.-à-d.), the latter
# kept on purpose for lessons written before the switch to English.
_ABBREVIATION = re.compile(
    r"(?:^|[\s(«\"'])(?:p\.\s?ex|etc|cf|env|m|e\.\s?g|i\.\s?e|c\.-à-d|ex|vs)\.$", re.IGNORECASE
)
_NEXT_LETTER = re.compile(r"\s*[*_`«\"'(\[]*(\S?)")
_ITEM_PREFIX = re.compile(r"^\s*(?:>\s?)*(?:[-*+]|\d+[.)])\s+")
_LINE_PREFIX = re.compile(r"^\s*(?:>\s?)*")

type Span = tuple[int, int]
type Hit = tuple[int, frozenset[int]]  # (paragraph, sentence ranks)


@dataclass(frozen=True)
class Pruned:
    markdown: str
    removed: int  # sentences removed
    unlocated: int  # claims not found, ambiguous or not removable


@dataclass(frozen=True)
class _Block:
    """A paragraph of the lesson, split into sentences."""

    section: str  # folded key of the `##` section that contains it
    lines: Span  # its lines `[start, end)`
    item: Span | None  # the list item of which it is the first block
    prefix: str  # list or quote marker of its first line
    sentences: list[str]
    words: list[tuple[str, int]]  # (normalized word, rank of its sentence)


def _words(text: str) -> list[str]:
    """Words without case, punctuation, link addresses or Markdown formatting."""
    return _WORD.findall(_LINK_TARGET.sub("]", text).casefold())


def _ends_sentence(text: str, match: re.Match[str]) -> bool:
    """No cut after an abbreviation ("e.g.", "etc.", "p. ex."...) or before a lowercase letter."""
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
    """The paragraphs of the lesson, and the lines of its code blocks."""
    lines = markdown.split("\n")
    tokens = _MD.parse(markdown)
    blocks: list[_Block] = []
    code: list[Span] = []
    section = ""
    for index, token in enumerate(tokens):
        span = _span(token)
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0:
            section = reading_section(tokens[index + 1].content) or ""
        elif token.type in ("fence", "code_block") and span is not None:
            code.append(span)
        elif token.type == "paragraph_open" and span is not None:
            before = tokens[index - 1] if index else None
            item = _span(before) if before and before.type == "list_item_open" else None
            blocks.append(_block(lines, span, item, section))
    return blocks, code


def fragment(claim: str) -> list[str] | None:
    """Words of the longest fragment of the claim's first quotation, or `None`."""
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
    """The single sentence (or run of sentences) that carries the quoted fragment; `None` if it is
    absent, present in several sentences, or too short for the bulk of its own."""
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
    """The claims to judge: located in a fact section, or not found (the Writer can still fix
    them). A claim located elsewhere only is discarded."""
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
    """The replacement of the paragraph's lines; `None` if it would take code away."""
    kept = [s for rank, s in enumerate(block.sentences) if rank not in ranks]
    if kept:
        return (*block.lines, [block.prefix + " ".join(kept)])
    if block.item is None:
        return (*block.lines, [])
    start, end = block.item
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1  # the blank line that follows the item stays: nothing gets glued back
    if any(start <= a and b <= end for a, b in code):
        return None  # a code block is never removed
    return (start, end, [])  # the whole item, sub-list included


def _apply(lines: list[str], edits: list[tuple[int, int, list[str]]]) -> str:
    """Applies the replacements; a replacement contained in another (sub-item of a removed item)
    is already carried away. Two overlapping replacements are an error."""
    outer: list[tuple[int, int, list[str]]] = []
    for edit in sorted(edits, key=lambda e: (e[0], -e[1])):
        if outer and edit[1] <= outer[-1][1]:
            continue
        if outer and edit[0] < outer[-1][1]:
            raise ValueError("Overlapping removals in the lesson.")
        outer.append(edit)
    for start, end, new in reversed(outer):
        lines[start:end] = new
    return "\n".join(lines)


def prune(markdown: str, claims: Sequence[str]) -> Pruned:
    """The lesson without the sentences that carry `claims` (in the fact sections only)."""
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
    """Claims whose quoted fragment still appears in the text (paragraphs, tables, headings;
    outside code): check after the removal."""
    texts = [_words(t.content) for t in _MD.parse(markdown) if t.type == "inline"]
    count = 0
    for claim in claims:
        words = fragment(claim)
        if words is not None and any(_occurs(found, words) for found in texts):
            count += 1
    return count

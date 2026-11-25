"""Quotations and copying (SPEC 3.5, D90): "nothing is copied" = no passage of more than 25
words identical to a source, outside a short quotation between « » followed by `[n]`. Words are
compared ignoring case and punctuation."""

import re
from collections.abc import Sequence

MAX_QUOTE_WORDS = 25
_QUOTE = re.compile(r"«([^»]*)»(\s*\[\d+\])?")
_PUNCTUATION = re.compile(r"\W")


def words_of(text: str) -> list[str]:
    """Words as a reader counts them (separated by spaces), ignoring case and punctuation."""
    return [word for token in text.casefold().split() if (word := _PUNCTUATION.sub("", token))]


def _windows(words: list[str]) -> set[tuple[str, ...]]:
    size = MAX_QUOTE_WORDS + 1
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def build_index(sources: Sequence[tuple[int, str, str]]) -> dict[tuple[str, ...], int]:
    """Each run of 26 words of a source, with the number of the first one that contains it."""
    index: dict[tuple[str, ...], int] = {}
    for number, _url, text in sources:
        for window in _windows(words_of(text)):
            index.setdefault(window, number)
    return index


def split_quotes(text: str) -> tuple[list[str], list[str]]:
    """`(text outside attributed quotations, attributed quotations)`: an attributed quotation is
    `« ... »` followed by `[n]`; a quotation without `[n]` stays running text."""
    outside: list[str] = []
    quotes: list[str] = []
    last = 0
    for match in _QUOTE.finditer(text):
        if match.group(2) is None:
            continue
        outside.append(text[last : match.start()])
        quotes.append(match.group(1))
        last = match.end()
    outside.append(text[last:])
    return outside, quotes


def copied_from(parts: Sequence[str], index: dict[tuple[str, ...], int]) -> set[int]:
    """Numbers of the sources of which a passage of more than 25 words appears in these pieces
    of text (each piece is compared alone: a removed quotation does not bring its neighbors
    together)."""
    found: set[int] = set()
    if not index:
        return found
    for part in parts:
        for window in _windows(words_of(part)):
            if (number := index.get(window)) is not None:
                found.add(number)
    return found

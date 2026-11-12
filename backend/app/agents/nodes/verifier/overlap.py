"""Citations et recopie (SPEC 3.5, D90) : « rien n'est recopié » = aucun passage de plus de 25
mots identique à une source, hors d'une citation courte entre « » suivie de `[n]`. Les mots sont
comparés sans casse ni ponctuation."""

import re
from collections.abc import Sequence

MAX_QUOTE_WORDS = 25
_QUOTE = re.compile(r"«([^»]*)»(\s*\[\d+\])?")
_PUNCTUATION = re.compile(r"\W")


def words_of(text: str) -> list[str]:
    """Mots comme un lecteur les compte (séparés par des espaces), sans casse ni ponctuation."""
    return [word for token in text.casefold().split() if (word := _PUNCTUATION.sub("", token))]


def _windows(words: list[str]) -> set[tuple[str, ...]]:
    size = MAX_QUOTE_WORDS + 1
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def build_index(sources: Sequence[tuple[int, str, str]]) -> dict[tuple[str, ...], int]:
    """Chaque suite de 26 mots d'une source, avec le numéro de la première qui la contient."""
    index: dict[tuple[str, ...], int] = {}
    for number, _url, text in sources:
        for window in _windows(words_of(text)):
            index.setdefault(window, number)
    return index


def split_quotes(text: str) -> tuple[list[str], list[str]]:
    """`(texte hors citation attribuée, citations attribuées)` : une citation attribuée est
    `« … »` suivie de `[n]` ; une citation sans `[n]` reste du texte courant."""
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
    """Numéros des sources dont un passage de plus de 25 mots figure dans ces morceaux de texte
    (chaque morceau est comparé seul : une citation retirée ne rapproche pas ses voisins)."""
    found: set[int] = set()
    if not index:
        return found
    for part in parts:
        for window in _windows(words_of(part)):
            if (number := index.get(window)) is not None:
                found.add(number)
    return found

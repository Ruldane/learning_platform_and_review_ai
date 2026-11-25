"""Cleaning queries before they are sent to a search engine (SPEC 17.3).

Removes emails, phone numbers, the user's full name and their family name (last word of the
name, at least three letters), ignoring case and accents. The first name alone is kept:
removing it would damage too many ordinary queries (D75).
"""

import re
import unicodedata
from dataclasses import dataclass

MIN_FAMILY_NAME = 3

_EMAIL = re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)+")
# International: « + » (or « 00 ») then 8 to 15 digits, separated by spaces, dots, dashes
# or parentheses (+33 6 12 34 56 78, +1 (415) 555-0100).
_INTERNATIONAL = re.compile(r"(?<!\w)(?:\+|00)[0-9](?:[ .\-]?\(?[0-9]\)?){7,14}(?!\w)")
# French national: 0X XX XX XX XX (optional separators).
_FRENCH = re.compile(r"(?<!\w)0[1-9](?:[ .\-]?[0-9]{2}){4}(?!\w)")


@dataclass(frozen=True)
class Identity:
    full_name: str | None
    email: str | None


def _fold(text: str) -> tuple[str, list[int]]:
    """Lowercase without accents, and for each character returned, the index of the original
    character."""
    folded: list[str] = []
    origin: list[int] = []
    for index, char in enumerate(text):
        for part in unicodedata.normalize("NFD", char):
            if unicodedata.combining(part):
                continue
            for low in part.lower():
                folded.append(low)
                origin.append(index)
    return "".join(folded), origin


def _word(words: list[str]) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(word) for word in words)
    # The dash also borders a word: « doe-reader » is not the name « doe ».
    return re.compile(rf"(?<![\w-]){body}(?![\w-])")


def _name_patterns(identity: Identity) -> list[re.Pattern[str]]:
    if not identity.full_name:
        return []
    words = _fold(identity.full_name)[0].split()
    patterns: list[re.Pattern[str]] = []
    if len(words) > 1:  # a single-word name is indistinguishable from a first name: kept
        patterns.append(_word(words))
        if len(words[-1]) >= MIN_FAMILY_NAME:
            patterns.append(_word([words[-1]]))
    return patterns


def scrub_query(query: str, identity: Identity) -> str:
    """`query` without email, phone, full name or family name; spaces collapsed."""
    folded, origin = _fold(query)
    patterns = [_EMAIL, _INTERNATIONAL, _FRENCH, *_name_patterns(identity)]
    drop = [False] * len(query)
    for pattern in patterns:
        for match in pattern.finditer(folded):
            if match.end() == match.start():
                continue
            start = origin[match.start()]
            end = origin[match.end() - 1] + 1
            while end < len(query) and unicodedata.combining(query[end]):
                end += 1  # a separate accent (e + U+0301) goes with its letter
            drop[start:end] = [True] * (end - start)
    kept = "".join(" " if gone else char for char, gone in zip(query, drop, strict=True))
    return " ".join(kept.split())

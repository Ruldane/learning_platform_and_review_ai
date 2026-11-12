"""Nettoyage des requêtes avant envoi à un moteur de recherche (SPEC 17.3).

Retire les emails, les numéros de téléphone, le nom complet de l'utilisateur et son nom de famille
(dernier mot du nom, trois lettres au moins), sans tenir compte de la casse ni des accents. Le
prénom seul est gardé : le retirer abîmerait trop de requêtes ordinaires (D75).
"""

import re
import unicodedata
from dataclasses import dataclass

MIN_FAMILY_NAME = 3

_EMAIL = re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)+")
# International : « + » (ou « 00 ») puis 8 à 15 chiffres, séparés par espaces, points, tirets
# ou parenthèses (+33 6 12 34 56 78, +1 (415) 555-0100).
_INTERNATIONAL = re.compile(r"(?<!\w)(?:\+|00)[0-9](?:[ .\-]?\(?[0-9]\)?){7,14}(?!\w)")
# National français : 0X XX XX XX XX (séparateurs facultatifs).
_FRENCH = re.compile(r"(?<!\w)0[1-9](?:[ .\-]?[0-9]{2}){4}(?!\w)")


@dataclass(frozen=True)
class Identity:
    full_name: str | None
    email: str | None


def _fold(text: str) -> tuple[str, list[int]]:
    """Minuscules sans accents, et pour chaque caractère rendu l'indice du caractère d'origine."""
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
    # Le tiret borde aussi un mot : « doe-reader » n'est pas le nom « doe ».
    return re.compile(rf"(?<![\w-]){body}(?![\w-])")


def _name_patterns(identity: Identity) -> list[re.Pattern[str]]:
    if not identity.full_name:
        return []
    words = _fold(identity.full_name)[0].split()
    patterns: list[re.Pattern[str]] = []
    if len(words) > 1:  # un nom d'un seul mot est indiscernable d'un prénom : gardé
        patterns.append(_word(words))
        if len(words[-1]) >= MIN_FAMILY_NAME:
            patterns.append(_word([words[-1]]))
    return patterns


def scrub_query(query: str, identity: Identity) -> str:
    """`query` sans email, téléphone, nom complet ni nom de famille ; espaces ramassés."""
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
                end += 1  # un accent séparé (e + U+0301) part avec sa lettre
            drop[start:end] = [True] * (end - start)
    kept = "".join(" " if gone else char for char, gone in zip(query, drop, strict=True))
    return " ".join(kept.split())

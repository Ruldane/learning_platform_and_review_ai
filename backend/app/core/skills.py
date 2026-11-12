"""Nom normalisé d'une compétence : clé de dédoublonnage du graphe et des acquis connus."""

import re
import unicodedata

_SPACES = re.compile(r"\s+")
# Ponctuation de bord retirée ; « + » et « # » restent (C++, C#).
_EDGE = " .,;:!?'\"«»()[]{}-_/\\"


def normalize_skill_name(name: str) -> str:
    """Sans accents, en minuscules (`casefold`), espaces ramassés, ponctuation de bord retirée."""
    decomposed = unicodedata.normalize("NFKD", name)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACES.sub(" ", plain.casefold()).strip(_EDGE)

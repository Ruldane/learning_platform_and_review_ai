"""Les notes du rapport de revue (SPEC 5.3, 18.3) : `ats_notes`, `strengths`, `risks`. Aucune
garantie de passage de l'ATS ni d'acceptation : le prompt le demande, ce filtre l'impose (revue
6.13 m6). Une phrase qui promet un passage, une acceptation ou un résultat certain est retirée ;
une note vidée disparaît. « Aucune garantie de passage » (la phrase honnête) reste."""

import re
from collections.abc import Iterable

from app.agents.tools.posting_schema import normalize_term

_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
# Une promesse, quelle que soit la tournure (texte sans casse ni accent).
_PROMISE = re.compile(
    r"\b(passera|passeras|passerez|va passer|vas passer|vont passer|sera accepte\w*|"
    r"sera retenu\w*|sera selectionne\w*|sera presele\w*|sera rejete\w*|sera lu|"
    r"a coup sur|sans aucun doute|est assure de|are sure to|will pass|will be accepted|"
    r"will get through|sure to pass|will not be rejected|ne sera pas rejete\w*)\b"
)
# « Garanti » en bonne place : sauf si la phrase le nie (« aucune garantie », « ne garantit pas »).
_GUARANTEE = re.compile(r"\b(garanti|garantie|garantis|garantit|garantira|guarantee|guaranteed)\b")
_NEGATED = re.compile(
    r"\b(aucune|aucun|pas de|pas|sans|ne|n|jamais|no|not|never)\b[^.!?]{0,40}"
    r"\b(garanti|garantie|garantis|garantit|guarantee|guaranteed|guarantees)\b"
)
# « 100 % » seulement s'il parle du passage ou du résultat (« 100 % des mots clés » est un fait).
_ABSOLUTE = re.compile(r"\b100 ?%")
_OUTCOME = re.compile(
    r"\b(ats|filtre|passage|passer|accept\w*|retenu\w*|selection\w*|succes|pass)\b"
)


def promises(sentence: str) -> bool:
    """La phrase promet un passage de l'ATS, une acceptation ou un résultat certain."""
    text = normalize_term(sentence)
    if _PROMISE.search(text):
        return True
    if _GUARANTEE.search(text) and not _NEGATED.search(text):
        return True
    return bool(_ABSOLUTE.search(sentence.casefold().replace(" ", " "))) and bool(
        _OUTCOME.search(text)
    )


def without_promises(notes: Iterable[str]) -> list[str]:
    """Les notes sans leurs phrases de promesse ; une note vidée est retirée."""
    kept: list[str] = []
    for note in notes:
        sentences = [s for s in _SENTENCES.split(note.strip()) if s.strip()]
        text = " ".join(s for s in sentences if not promises(s))
        if text.strip():
            kept.append(text.strip())
    return kept

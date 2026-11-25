"""Notes of the review report (SPEC 5.3, 18.3): `ats_notes`, `strengths`, `risks`. No guarantee
of passing the ATS nor of acceptance: the prompt asks for it, this filter enforces it (review
6.13 m6). A sentence that promises a pass, an acceptance or a certain result is removed;
an emptied note disappears. "Aucune garantie de passage" (the honest sentence) stays."""

import re
from collections.abc import Iterable

from app.agents.tools.posting_schema import normalize_term

_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
# A promise, whatever the wording (text without case or accent).
_PROMISE = re.compile(
    r"\b(passera|passeras|passerez|va passer|vas passer|vont passer|sera accepte\w*|"
    r"sera retenu\w*|sera selectionne\w*|sera presele\w*|sera rejete\w*|sera lu|"
    r"a coup sur|sans aucun doute|est assure de|are sure to|will pass|will be accepted|"
    r"will get through|sure to pass|will not be rejected|ne sera pas rejete\w*)\b"
)
# "Garanti" in a prominent spot, unless denied ("aucune garantie", "ne garantit pas").
_GUARANTEE = re.compile(r"\b(garanti|garantie|garantis|garantit|garantira|guarantee|guaranteed)\b")
_NEGATED = re.compile(
    r"\b(aucune|aucun|pas de|pas|sans|ne|n|jamais|no|not|never)\b[^.!?]{0,40}"
    r"\b(garanti|garantie|garantis|garantit|guarantee|guaranteed|guarantees)\b"
)
# "100 %" only if it talks about the pass or the result ("100 % des mots clés" is a fact).
_ABSOLUTE = re.compile(r"\b100 ?%")
_OUTCOME = re.compile(
    r"\b(ats|filtre|passage|passer|accept\w*|retenu\w*|selection\w*|succes|pass)\b"
)


def promises(sentence: str) -> bool:
    """The sentence promises an ATS pass, an acceptance or a certain result."""
    text = normalize_term(sentence)
    if _PROMISE.search(text):
        return True
    if _GUARANTEE.search(text) and not _NEGATED.search(text):
        return True
    return bool(_ABSOLUTE.search(sentence.casefold().replace(" ", " "))) and bool(
        _OUTCOME.search(text)
    )


def without_promises(notes: Iterable[str]) -> list[str]:
    """The notes without their promise sentences; an emptied note is removed."""
    kept: list[str] = []
    for note in notes:
        sentences = [s for s in _SENTENCES.split(note.strip()) if s.strip()]
        text = " ".join(s for s in sentences if not promises(s))
        if text.strip():
            kept.append(text.strip())
    return kept

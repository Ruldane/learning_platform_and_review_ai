"""File name of a produced CV (D118): ASCII, readable, never empty. It contains January's
name: never logged."""

import re
import unicodedata

MAX_PART = 40
_NOT_KEPT = re.compile(r"[^A-Za-z0-9-]")
# Ligatures and letters that NFKD does not decompose.
_LIGATURES = str.maketrans({"œ": "oe", "Œ": "Oe", "æ": "ae", "Æ": "Ae", "ß": "ss"})


def _part(text: str | None) -> str:
    """One part of the name: ligatures expanded, accents removed, words joined by "_",
    characters outside `[A-Za-z0-9-]` removed (a word made only of dashes too), 40 characters
    at most (without a trailing "_" or "-"). A non-Latin name disappears."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.translate(_LIGATURES))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = [_NOT_KEPT.sub("", word) for word in plain.split()]
    joined = "_".join(word for word in words if word.strip("-"))
    return joined[:MAX_PART].rstrip("_-")


def cv_filename(name: str, company: str | None, title: str | None) -> str:
    """ "CV_<Name>_<Company>_<Role>.pdf"; an empty part is omitted, "CV.pdf" at worst."""
    parts = [part for part in (_part(name), _part(company), _part(title)) if part]
    return "_".join(["CV", *parts]) + ".pdf"


def kit_filename(company: str | None, title: str | None) -> str:
    """ "Kit_<Company>_<Role>.zip" (application kit archive); "Kit.zip" at worst."""
    parts = [part for part in (_part(company), _part(title)) if part]
    return "_".join(["Kit", *parts]) + ".zip"

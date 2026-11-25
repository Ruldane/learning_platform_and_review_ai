"""Skills: normalised name (deduplication key of the graph and of the known achievements) and
structured evidence of a level (D99)."""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict, cast, get_args

_SPACES = re.compile(r"\s+")
# Edge punctuation removed; "+" and "#" stay (C++, C#).
_EDGE = " .,;:!?'\"«»()[]{}-_/\\"


def normalize_skill_name(name: str) -> str:
    """Without accents, lowercase (`casefold`), spaces collapsed, edge punctuation removed."""
    decomposed = unicodedata.normalize("NFKD", name)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACES.sub(" ", plain.casefold()).strip(_EDGE)


EvidenceKind = Literal[
    "program",
    "lesson",
    "study",
    "quiz",
    "project",
    "cv",
    "capture",
    "ide",
    "github",
    "system_design",
    "contribution",
    "feynman",
]
_KINDS: frozenset[str] = frozenset(get_args(EvidenceKind))


class Evidence(TypedDict):
    """Evidence of a level: where it comes from. `ref_id` designates the object (quiz, session,
    program...); `at` is an ISO instant in UTC, empty for a phase 4 evidence."""

    kind: EvidenceKind
    ref_id: str | None
    label: str
    at: str


def evidence(kind: EvidenceKind, ref_id: str | None, label: str, at: datetime) -> Evidence:
    """Evidence dated at `at` (an instant with a time zone, rendered in UTC)."""
    if at.tzinfo is None:
        raise ValueError("datetime without a time zone refused (UTC expected)")
    return Evidence(kind=kind, ref_id=ref_id, label=label, at=at.astimezone(UTC).isoformat())


def _kind_of(value: object) -> EvidenceKind | None:
    return cast(EvidenceKind, value) if isinstance(value, str) and value in _KINDS else None


def read_evidence(raw: Sequence[Any]) -> list[Evidence]:
    """The evidence of a level, read from the database. A phase 4 string becomes a `program`
    evidence without reference or date; whatever is neither is ignored."""
    out: list[Evidence] = []
    for item in raw:
        if isinstance(item, str):
            out.append(Evidence(kind="program", ref_id=None, label=item, at=""))
        elif isinstance(item, Mapping):
            kind = _kind_of(item.get("kind"))
            if kind is None:
                continue
            ref_id = item.get("ref_id")
            out.append(
                Evidence(
                    kind=kind,
                    ref_id=ref_id if isinstance(ref_id, str) else None,
                    label=str(item.get("label", "")),
                    at=str(item.get("at", "")),
                )
            )
    return out

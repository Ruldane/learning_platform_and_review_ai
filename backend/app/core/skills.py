"""Compétences : nom normalisé (clé de dédoublonnage du graphe et des acquis connus) et preuves
structurées d'un niveau (D99)."""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict, cast, get_args

_SPACES = re.compile(r"\s+")
# Ponctuation de bord retirée ; « + » et « # » restent (C++, C#).
_EDGE = " .,;:!?'\"«»()[]{}-_/\\"


def normalize_skill_name(name: str) -> str:
    """Sans accents, en minuscules (`casefold`), espaces ramassés, ponctuation de bord retirée."""
    decomposed = unicodedata.normalize("NFKD", name)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACES.sub(" ", plain.casefold()).strip(_EDGE)


EvidenceKind = Literal["program", "lesson", "study", "quiz", "project", "cv", "capture"]
_KINDS: frozenset[str] = frozenset(get_args(EvidenceKind))


class Evidence(TypedDict):
    """Une preuve d'un niveau : d'où il vient. `ref_id` désigne l'objet (quiz, session,
    programme…) ; `at` est un instant ISO en UTC, vide pour une preuve de la phase 4."""

    kind: EvidenceKind
    ref_id: str | None
    label: str
    at: str


def evidence(kind: EvidenceKind, ref_id: str | None, label: str, at: datetime) -> Evidence:
    """Une preuve datée à `at` (un instant avec fuseau, rendu en UTC)."""
    if at.tzinfo is None:
        raise ValueError("datetime sans fuseau horaire refusé (UTC attendu)")
    return Evidence(kind=kind, ref_id=ref_id, label=label, at=at.astimezone(UTC).isoformat())


def _kind_of(value: object) -> EvidenceKind | None:
    return cast(EvidenceKind, value) if isinstance(value, str) and value in _KINDS else None


def read_evidence(raw: Sequence[Any]) -> list[Evidence]:
    """Les preuves d'un niveau, lues de la base. Une chaîne de la phase 4 devient une preuve
    `program` sans référence ni date ; ce qui n'est ni l'une ni l'autre est ignoré."""
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

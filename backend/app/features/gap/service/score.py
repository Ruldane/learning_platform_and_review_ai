"""Score de match d'une offre et compétences les plus manquantes (SPEC F8, D118)."""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from app.core.skills import normalize_skill_name
from app.db.models.skills import SkillLevel

REQUIRED_WEIGHT = 2
PREFERRED_WEIGHT = 1
LEVEL_VALUE: dict[SkillLevel | None, float] = {
    "valide": 1.0,
    "prouve": 1.0,
    "declare": 0.6,
    "en_cours": 0.3,
    None: 0.0,
}
# Les mêmes valeurs en dixièmes : le score se calcule en entiers.
LEVEL_TENTHS: dict[SkillLevel | None, int] = {
    level: round(value * 10) for level, value in LEVEL_VALUE.items()
}
TOP_MISSING = 10

GapAction = Literal["in_program", "to_add", "out_of_scope"]
GapSource = Literal["posting", "cv_review"]


@dataclass(frozen=True)
class GapRow:
    """Une ligne de l'écart : une compétence de l'offre (ou un mot clé relevé par une revue de
    CV, `source="cv_review"`), le niveau de January et ce qu'on en fait."""

    skill: str
    required: bool
    level: SkillLevel | None
    action: GapAction
    week: int | None
    source: GapSource = "posting"


@dataclass(frozen=True)
class MissingSkill:
    """Une compétence absente : `postings` offres la demandent, dont `required_in` comme
    obligatoire (preflight G4)."""

    skill: str
    postings: int
    required_in: int


def match_score(rows: Sequence[GapRow]) -> int:
    """`round(100 × Σ poids × valeur / Σ poids)` (arrondi au plus proche, ,5 vers le haut) sur
    les lignes de l'offre seulement : celles d'une revue de CV ne changent pas le score (G3).
    Aucune ligne : 0."""
    counted = [row for row in rows if row.source == "posting"]
    total = sum(_weight(row) for row in counted)
    if total == 0:
        return 0
    # En entiers (valeurs en dixièmes) : 0,6 et 0,3 ne sont pas exacts en flottant, et 57,5
    # tomberait à 57. score = ⌊10 × earned / total + ½⌋ = (20 × earned + total) // (2 × total).
    earned = sum(_weight(row) * LEVEL_TENTHS[row.level] for row in counted)
    return (20 * earned + total) // (2 * total)


def _weight(row: GapRow) -> int:
    return REQUIRED_WEIGHT if row.required else PREFERRED_WEIGHT


def top_missing(gaps: Iterable[Sequence[GapRow]], limit: int = TOP_MISSING) -> list[MissingSkill]:
    """Les compétences absentes (niveau `None` : jamais acquises, même déclarée n'en est pas
    une), comptées une fois par offre (nom normalisé), triées par nombre d'offres décroissant
    puis par nom ; `limit` au plus. `gaps` : les lignes de chaque offre."""
    postings: Counter[str] = Counter()
    required: Counter[str] = Counter()
    names: dict[str, str] = {}
    for rows in gaps:
        seen: dict[str, bool] = {}
        for row in rows:
            if row.level is not None:
                continue
            key = normalize_skill_name(row.skill)
            names.setdefault(key, row.skill)
            seen[key] = seen.get(key, False) or row.required
        postings.update(seen.keys())
        required.update(key for key, is_required in seen.items() if is_required)
    ranked = sorted(postings, key=lambda key: (-postings[key], key))
    return [MissingSkill(names[key], postings[key], required[key]) for key in ranked[:limit]]

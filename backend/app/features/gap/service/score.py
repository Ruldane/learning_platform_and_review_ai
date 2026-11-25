"""Match score of an offer and the most missing skills (SPEC F8, D118)."""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from app.core.skills import normalize_skill_name
from app.db.models.skills import SkillLevel

REQUIRED_WEIGHT = 2
PREFERRED_WEIGHT = 1
LEVEL_VALUE: dict[SkillLevel | None, float] = {
    "validated": 1.0,
    "proven": 1.0,
    "declared": 0.6,
    "in_progress": 0.3,
    None: 0.0,
}
# The same values in tenths: the score is computed in integers.
LEVEL_TENTHS: dict[SkillLevel | None, int] = {
    level: round(value * 10) for level, value in LEVEL_VALUE.items()
}
TOP_MISSING = 10

GapAction = Literal["in_program", "to_add", "out_of_scope"]
GapSource = Literal["posting", "cv_review"]


@dataclass(frozen=True)
class GapRow:
    """A gap row: one skill of the offer (or a keyword raised by a CV review,
    `source="cv_review"`), January's level and what is done about it."""

    skill: str
    required: bool
    level: SkillLevel | None
    action: GapAction
    week: int | None
    source: GapSource = "posting"


@dataclass(frozen=True)
class MissingSkill:
    """A missing skill: `postings` offers ask for it, of which `required_in` as required
    (preflight G4)."""

    skill: str
    postings: int
    required_in: int


def match_score(rows: Sequence[GapRow]) -> int:
    """`round(100 × Σ weight × value / Σ weight)` (rounded to nearest, halves up) over the rows
    of the offer only: those of a CV review do not change the score (G3). No rows: 0."""
    counted = [row for row in rows if row.source == "posting"]
    total = sum(_weight(row) for row in counted)
    if total == 0:
        return 0
    # In integers (values in tenths): 0.6 and 0.3 are not exact in floating point, and 57.5
    # would fall to 57. score = ⌊10 × earned / total + ½⌋ = (20 × earned + total) // (2 × total).
    earned = sum(_weight(row) * LEVEL_TENTHS[row.level] for row in counted)
    return (20 * earned + total) // (2 * total)


def _weight(row: GapRow) -> int:
    return REQUIRED_WEIGHT if row.required else PREFERRED_WEIGHT


def top_missing(gaps: Iterable[Sequence[GapRow]], limit: int = TOP_MISSING) -> list[MissingSkill]:
    """The missing skills (level `None`: never acquired; a merely declared one does not count),
    counted once per offer (normalized name), sorted by number of offers descending then by name;
    `limit` at most. `gaps`: the rows of each offer."""
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

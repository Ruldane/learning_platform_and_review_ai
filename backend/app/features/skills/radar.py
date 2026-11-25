"""Skills radar per domain and score of the curve (SPEC F15, D99, D107): pure rules.
Outside `service` to avoid a cycle with `program` (see 5.10)."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from math import floor

from app.db.models.skills import LEVEL_ORDER, SkillLevel

LEVEL_SCORE: dict[SkillLevel | None, int] = {
    None: 0,
    "declared": 25,
    "in_progress": 50,
    "validated": 75,
    "proven": 100,
}
OTHER_DOMAIN = "Other"
LEGACY_OTHER_DOMAIN = "Autres"  # the French label stored before the switch to English


def as_level(value: str) -> SkillLevel:
    """The level stored in the database; an unknown value reads as `declared`."""
    for level in LEVEL_ORDER:
        if level == value:
            return level
    return "declared"


def domain_name(domain: str | None) -> str:
    """The displayed domain: "Other" for a skill without a domain."""
    name = (domain or "").strip()
    return OTHER_DOMAIN if name in ("", LEGACY_OTHER_DOMAIN) else name


def _rounded_mean(values: Sequence[int]) -> int:
    return floor(sum(values) / len(values) + 0.5) if values else 0


def domain_scores(rows: Sequence[tuple[str | None, SkillLevel | None]]) -> list[tuple[str, int]]:
    """The mean of the level scores per domain (integer, 0.5 rounded up), sorted by name; a
    skill without a domain goes into "Other"."""
    scores: dict[str, list[int]] = defaultdict(list)
    for domain, level in rows:
        scores[domain_name(domain)].append(LEVEL_SCORE[level])
    return [
        (name, _rounded_mean(values))
        for name, values in sorted(scores.items(), key=lambda item: item[0].casefold())
    ]


def mean_score(levels: Sequence[SkillLevel]) -> int:
    """The score of a snapshot (progress curve, D107): mean of the level scores of the skills
    that have a level, 0.5 rounded up; 0 without a skill."""
    return _rounded_mean([LEVEL_SCORE[level] for level in levels])


def level_counts(levels: Iterable[SkillLevel]) -> dict[SkillLevel, int]:
    """The number of skills per level, the four levels always present."""
    counts: dict[SkillLevel, int] = dict.fromkeys(LEVEL_ORDER, 0)
    for level in levels:
        counts[level] += 1
    return counts

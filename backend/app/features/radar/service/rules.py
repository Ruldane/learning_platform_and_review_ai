"""Pure rules of the market radar (P5 to P9): ranking of requested skills, change over time,
"absent from your program" alerts, score of an offer, kept salary, enrichment of the reference
data. Nothing here imports the database; only the match score comes from `gap`."""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any

from app.core.skills import normalize_skill_name
from app.db.models.skills import SkillLevel
from app.features.gap.service.score import GapRow, match_score

MIN_RUN = 30
MAX_RUN = 50
MAX_READS = 60
MAX_CANDIDATES = 80
HIGH_MATCH = 70
ALERT_SHARE = 0.5
ALERT_MIN_POSTINGS = 10
ALERT_MAX = 5
ENRICH_SHARE = 0.3
ENRICH_MAX = 15

_DIGITS = re.compile(r"\d+")
_ACQUIRED: frozenset[str] = frozenset({"validated", "proven"})


@dataclass(frozen=True)
class SkillFreq:
    """A skill in the ranking: requested by `count` analysed offers, i.e. `share` (rounded to 0.01),
    at rank `rank` (ties share their rank)."""

    skill: str
    norm: str
    count: int
    share: float
    rank: int


@dataclass(frozen=True)
class SkillTrend(SkillFreq):
    """A ranking row with its change since the previous scan: `delta_share` in percentage points,
    `delta_rank` in ranks gained (positive) or lost; `new`: absent from the previous scan. Without a
    previous scan: deltas at `None`, `new` false."""

    delta_share: float | None
    delta_rank: int | None
    new: bool


@dataclass(frozen=True)
class Alert:
    """A highly requested skill absent from the program (rule P8)."""

    skill: str
    share: float
    message: str


def _percent(count: int, total: int) -> int:
    """`count / total` as a whole percentage, rounded to the nearest (0.5 rounds up), as
    integers."""
    return (200 * count + total) // (2 * total)


def _skill_names(posting: Mapping[str, Any]) -> dict[str, str]:
    """The skills of an offer: normalized name → name as written (the first form), once each."""
    names: dict[str, str] = {}
    for item in posting.get("skills") or []:
        name = str(item.get("name") or "").strip()
        norm = normalize_skill_name(name)
        if norm:
            names.setdefault(norm, name)
    return names


def rank_skills(postings: Sequence[Mapping[str, Any]]) -> list[SkillFreq]:
    """The ranking of the skills of the offers read (`read == "ok"`) and analysed (`skills` is a
    list, even an empty one). A skill counts once per offer (normalized name); it is shown in its
    most frequent form; `share` = `count` / analysed offers, rounded to 0.01; sorted by `count`
    descending, then normalized name; ranks 1, 2, 2, 4 (ties)."""
    analysed = [p for p in postings if p.get("read") == "ok" and isinstance(p.get("skills"), list)]
    counts: Counter[str] = Counter()
    forms: dict[str, Counter[str]] = {}
    for posting in analysed:
        names = _skill_names(posting)
        counts.update(names.keys())
        for norm, name in names.items():
            forms.setdefault(norm, Counter())[name] += 1
    ordered = sorted(counts, key=lambda norm: (-counts[norm], norm))
    out: list[SkillFreq] = []
    for position, norm in enumerate(ordered, start=1):
        rank = out[-1].rank if out and out[-1].count == counts[norm] else position
        display = min(forms[norm], key=lambda form: (-forms[norm][form], form))
        share = _percent(counts[norm], len(analysed)) / 100
        out.append(SkillFreq(display, norm, counts[norm], share, rank))
    return out


def evolution(
    current: Sequence[SkillFreq], previous: Sequence[SkillFreq] | None
) -> list[SkillTrend]:
    """The ranking `current` with its change since `previous` (same job, same area), by normalized
    name: share gap in points (integer), rank gained (old − new), `new` for a skill absent before.
    Without a previous scan: everything at `None` and `new` false."""
    before = None if previous is None else {item.norm: item for item in previous}
    trends: list[SkillTrend] = []
    for item in current:
        old = None if before is None else before.get(item.norm)
        points = None if old is None else round(item.share * 100) - round(old.share * 100)
        gained = None if old is None else old.rank - item.rank
        trends.append(
            SkillTrend(
                item.skill,
                item.norm,
                item.count,
                item.share,
                item.rank,
                delta_share=points,
                delta_rank=gained,
                new=before is not None and old is None,
            )
        )
    return trends


def alert_message(share: float) -> str:
    """Describe a skill that appears often in postings and is missing from the program."""
    return f"Requested in {round(share * 100)}% of postings and missing from your program."


def program_alerts(
    ranking: Sequence[SkillFreq],
    analyzed: int,
    in_program: AbstractSet[str],
    levels: Mapping[str, SkillLevel],
) -> list[Alert]:
    """Rule P8: at least `ALERT_MIN_POSTINGS` analysed offers; a skill requested by at least half of
    them, absent from every non-skipped module (`in_program`: normalized names, reference synonyms
    included) and at a level below `valide` (`levels`: by normalized name); `ALERT_MAX` at most, in
    ranking order."""
    if analyzed < ALERT_MIN_POSTINGS:
        return []
    alerts = [
        Alert(item.skill, item.share, alert_message(item.share))
        for item in ranking
        if item.share >= ALERT_SHARE
        and item.norm not in in_program
        and levels.get(item.norm) not in _ACQUIRED
    ]
    return alerts[:ALERT_MAX]


def posting_score(skills: Sequence[Mapping[str, Any]], levels: Mapping[str, SkillLevel]) -> int:
    """The match score of a radar offer (`match_score`, D118): each skill is a `to_add` row at the
    level read, by normalized name, counted once (required if one of its forms is). No skill: 0."""
    required: dict[str, bool] = {}
    names: dict[str, str] = {}
    for item in skills:
        name = str(item.get("name") or "").strip()
        norm = normalize_skill_name(name)
        if norm:
            names.setdefault(norm, name)
            required[norm] = required.get(norm, False) or bool(item.get("required"))
    rows = [GapRow(names[norm], required[norm], levels.get(norm), "to_add", None) for norm in names]
    return match_score(rows)


def salary_shown(salary: str | None, text: str) -> str | None:
    """The salary read by the model, kept only if each of its numbers appears in the offer text
    (whole number of digits: 45 is not 450). A salary without any digit, empty or absent: `None`."""
    figures = _DIGITS.findall(salary or "")
    if not figures:
        return None
    present = set(_DIGITS.findall(text))
    return (salary or "").strip() if all(figure in present for figure in figures) else None


def enrich_names(ranking: Sequence[SkillFreq]) -> list[str]:
    """The skills to add to the reference data (F15): requested by at least 30% of the offers,
    `ENRICH_MAX` at most, in ranking order."""
    return [item.skill for item in ranking if item.share >= ENRICH_SHARE][:ENRICH_MAX]


def low_sample(read_ok: int) -> bool:
    """True if the scan has fewer than `MIN_RUN` readable offers: the report says so."""
    return read_ok < MIN_RUN

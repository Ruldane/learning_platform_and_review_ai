"""Projection de l'adéquation aux offres à partir du travail prévu et du rythme réel."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Literal

from app.core.clock import week_start
from app.core.skills import normalize_skill_name
from app.features.gap.service.score import GapRow, match_score
from app.features.radar.service.rules import HIGH_MATCH, low_sample

HISTORY_WEEKS = 4
_MIN_HISTORY_WEEKS = 2
_DAYS_PER_WEEK = 7
_ACQUIRED = frozenset({"valide", "prouve"})
_RECOMMENDATIONS = 5

ScenarioKind = Literal["observed", "planned", "alternative"]
Uncertainty = Literal[
    "insufficient_study_history", "no_offer_sample", "small_offer_sample", "no_planned_chapters"
]


@dataclass(frozen=True)
class ChapterWork:
    program_id: str
    module_id: str
    lesson_id: str | None
    title: str
    minutes: int
    skills: tuple[str, ...]


@dataclass(frozen=True)
class ProjectionInput:
    today: date
    history_started_on: date | None = None
    studied: tuple[tuple[date, int], ...] = ()
    planned_weekly_minutes: int = 0
    alternative_weekly_minutes: int | None = None
    target_percent: int = 60
    offers: tuple[tuple[GapRow, ...], ...] = ()
    chapters: tuple[ChapterWork, ...] = ()  # dans l'ordre du travail prévu
    skill_aliases: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    kind: ScenarioKind
    weekly_minutes: int | None
    target_date: date | None
    projected_percent: int | None  # part à la fin du travail prévu


@dataclass(frozen=True)
class Recommendation:
    chapter: ChapterWork
    offers_unlocked: int
    offers_improved: int
    score_points: int


@dataclass(frozen=True)
class Projection:
    offer_count: int
    current_percent: int | None
    target_percent: int
    observed_weeks: int
    scenarios: tuple[Scenario, ...]
    recommendations: tuple[Recommendation, ...]
    uncertainty: tuple[Uncertainty, ...]


@dataclass(frozen=True)
class _Assessment:
    score: int
    credible: bool


@dataclass(frozen=True)
class _Milestone:
    work_minutes: int
    percent: int


def _observed(data: ProjectionInput) -> tuple[int, int | None]:
    if data.history_started_on is None:
        return 0, None
    end = week_start(data.today)
    first_full_week = week_start(data.history_started_on + timedelta(days=_DAYS_PER_WEEK - 1))
    weeks = max(0, min(HISTORY_WEEKS, (end - first_full_week).days // _DAYS_PER_WEEK))
    if weeks < _MIN_HISTORY_WEEKS:
        return weeks, None
    first = end - timedelta(weeks=weeks)
    total = sum(minutes for day, minutes in data.studied if first <= day < end)
    return weeks, total // weeks


def _assess(rows: tuple[GapRow, ...], learned: frozenset[str]) -> _Assessment:
    forecast = [
        replace(row, level="valide")
        if row.action != "out_of_scope" and row.level not in _ACQUIRED and row.skill in learned
        else row
        for row in rows
    ]
    score = match_score(forecast)
    return _Assessment(
        score,
        score >= HIGH_MATCH and all(row.level in _ACQUIRED for row in forecast if row.required),
    )


def _assess_all(
    offers: tuple[tuple[GapRow, ...], ...], learned: frozenset[str] = frozenset()
) -> tuple[_Assessment, ...]:
    return tuple(_assess(rows, learned) for rows in offers)


def _percent(assessments: tuple[_Assessment, ...]) -> int:
    return 100 * sum(assessment.credible for assessment in assessments) // len(assessments)


def skill_key(name: str, aliases: Mapping[str, str]) -> str:
    normalized = normalize_skill_name(name)
    return aliases.get(normalized, normalized)


def _milestones(
    offers: tuple[tuple[GapRow, ...], ...],
    chapters: tuple[tuple[ChapterWork, frozenset[str]], ...],
    current: tuple[_Assessment, ...],
) -> tuple[_Milestone, ...]:
    if not offers:
        return ()
    work, learned = 0, frozenset[str]()
    milestones = [_Milestone(0, _percent(current))]
    for chapter, skills in chapters:
        work += chapter.minutes
        if skills <= learned:
            continue
        learned |= skills
        percent = _percent(_assess_all(offers, learned))
        if percent > milestones[-1].percent:
            milestones.append(_Milestone(work, percent))
    return tuple(milestones)


def _scenario(
    kind: ScenarioKind,
    weekly: int | None,
    data: ProjectionInput,
    milestones: tuple[_Milestone, ...],
) -> Scenario:
    if not milestones:
        return Scenario(kind, weekly, None, None)
    reachable = milestones if weekly else milestones[:1]
    target = next((m for m in reachable if m.percent >= data.target_percent), None)
    when = None
    if target is not None:
        days = (target.work_minutes * _DAYS_PER_WEEK + weekly - 1) // weekly if weekly else 0
        when = data.today + timedelta(days=days)
    return Scenario(kind, weekly, when, reachable[-1].percent)


def _recommend(
    offers: tuple[tuple[GapRow, ...], ...],
    chapters: tuple[tuple[ChapterWork, frozenset[str]], ...],
    current: tuple[_Assessment, ...],
) -> tuple[Recommendation, ...]:
    items: list[Recommendation] = []
    for chapter, skills in chapters:
        changed = _assess_all(offers, skills)
        diff = tuple(zip(current, changed, strict=True))
        unlocked = sum(after.credible and not before.credible for before, after in diff)
        improved = sum(after.score > before.score for before, after in diff)
        if improved:
            gain = sum(after.score - before.score for before, after in diff)
            items.append(Recommendation(chapter, unlocked, improved, gain))
    items.sort(key=lambda item: (-item.offers_unlocked, -item.offers_improved, -item.score_points))
    return tuple(items[:_RECOMMENDATIONS])


def _uncertainty(
    weeks: int, offer_count: int, has_chapters: bool, current: int | None, goal: int
) -> tuple[Uncertainty, ...]:
    reasons: list[Uncertainty] = []
    if weeks < _MIN_HISTORY_WEEKS:
        reasons.append("insufficient_study_history")
    if not offer_count:
        reasons.append("no_offer_sample")
    elif low_sample(offer_count):
        reasons.append("small_offer_sample")
    if current is not None and current < goal and not has_chapters:
        reasons.append("no_planned_chapters")
    return tuple(reasons)


def project(data: ProjectionInput) -> Projection:
    """Une offre est crédible au seuil de bon match du radar et avec l'obligatoire acquis.

    La projection suppose que finir un chapitre valide les compétences qu'il vise. Les
    recommandations mesurent le gain d'un chapitre pris seul sur les compétences actuelles.
    """
    weeks, observed = _observed(data)
    aliases = data.skill_aliases
    rows = (
        tuple(
            replace(row, skill=skill_key(row.skill, aliases))
            for row in offer
            if row.source == "posting"
        )
        for offer in data.offers
    )
    offers = tuple(offer for offer in rows if offer)
    chapters = tuple(
        (chapter, frozenset(skill_key(name, aliases) for name in chapter.skills))
        for chapter in data.chapters
        if chapter.minutes > 0
    )
    current = _assess_all(offers)
    milestones = _milestones(offers, chapters, current)
    rates: list[tuple[ScenarioKind, int | None]] = [
        ("observed", observed),
        ("planned", data.planned_weekly_minutes),
    ]
    if data.alternative_weekly_minutes is not None:
        rates.append(("alternative", data.alternative_weekly_minutes))
    percent = _percent(current) if offers else None
    return Projection(
        offer_count=len(offers),
        current_percent=percent,
        target_percent=data.target_percent,
        observed_weeks=weeks,
        scenarios=tuple(_scenario(kind, rate, data, milestones) for kind, rate in rates),
        recommendations=_recommend(offers, chapters, current),
        uncertainty=_uncertainty(weeks, len(offers), bool(chapters), percent, data.target_percent),
    )

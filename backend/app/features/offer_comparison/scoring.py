"""La même base de comparaison est utilisée pour les deux offres."""

from dataclasses import dataclass
from unicodedata import normalize

from app.features.offer_comparison.schemas import (
    OfferComparisonAssessment,
    OfferComparisonPreferences,
    OfferComparisonResult,
    OfferComparisonScores,
    OfferCriterion,
    OfferLeader,
    OfferWeightSensitivity,
    OfferWorkMode,
)

CRITERIA: tuple[OfferCriterion, ...] = ("match", "work_mode", "location")
_WORK_MODES: dict[str, OfferWorkMode] = {
    "à distance": "remote",
    "100 % télétravail": "remote",
    "100% télétravail": "remote",
    "full remote": "remote",
    "remote": "remote",
    "télétravail intégral": "remote",
    "total": "remote",
    "hybride": "hybrid",
    "hybrid": "hybrid",
    "partiel": "hybrid",
    "télétravail partiel": "hybrid",
    "sur site": "onsite",
    "présentiel": "onsite",
    "aucun": "onsite",
    "none": "onsite",
    "onsite": "onsite",
    "on-site": "onsite",
}


def _key(value: str) -> str:
    return " ".join(normalize("NFC", value).casefold().split())


@dataclass(frozen=True)
class OfferFacts:
    id: str
    title: str | None
    company: str | None
    match: int | None
    remote: str | None
    location: str | None


def _assessment(
    facts: OfferFacts, preferences: OfferComparisonPreferences
) -> OfferComparisonAssessment:
    mode = _WORK_MODES.get(_key(facts.remote)) if facts.remote else None
    location = _key(facts.location) if facts.location else ""
    preferred = preferences.preferred_location
    scores = OfferComparisonScores(
        match=facts.match,
        work_mode=(
            100 * (mode == preferences.preferred_work_mode)
            if mode and preferences.preferred_work_mode
            else None
        ),
        location=100 * (location == _key(preferred)) if location and preferred else None,
    )
    missing = [
        key
        for key, present in zip(CRITERIA, (facts.match is not None, mode, location), strict=True)
        if not present
    ]
    return OfferComparisonAssessment(
        id=facts.id,
        title=facts.title,
        company=facts.company,
        location=facts.location,
        remote=facts.remote,
        scores=scores,
        missing=missing,
    )


@dataclass(frozen=True)
class Ranking:
    scores: tuple[float | None, float | None]
    leader: OfferLeader | None
    margin: float | None
    criteria: list[OfferCriterion]


def _ranking(
    first: OfferComparisonScores, second: OfferComparisonScores, weights: dict[str, int]
) -> Ranking:
    active: list[OfferCriterion] = []
    total = score_a = score_b = 0
    for criterion in CRITERIA:
        a, b, weight = getattr(first, criterion), getattr(second, criterion), weights[criterion]
        if weight == 0 or a is None or b is None:
            continue
        active.append(criterion)
        total += weight
        score_a += a * weight
        score_b += b * weight
    if not total:
        return Ranking((None, None), None, None, active)
    leader: OfferLeader = "first" if score_a > score_b else "second" if score_b > score_a else "tie"
    return Ranking(
        (round(score_a / total, 2), round(score_b / total, 2)),
        leader,
        round((score_a - score_b) / total, 2),
        active,
    )


def _sensitivity(
    first: OfferComparisonScores,
    second: OfferComparisonScores,
    weights: dict[str, int],
    criterion: OfferCriterion,
) -> OfferWeightSensitivity:
    low, high = max(0, weights[criterion] - 10), min(100, weights[criterion] + 10)
    lower = _ranking(first, second, {**weights, criterion: low})
    higher = _ranking(first, second, {**weights, criterion: high})
    return OfferWeightSensitivity(
        criterion=criterion,
        lower_weight=low,
        higher_weight=high,
        lower_leader=lower.leader,
        higher_leader=higher.leader,
        lower_margin=lower.margin,
        higher_margin=higher.margin,
    )


def compare(
    left: OfferFacts, right: OfferFacts, preferences: OfferComparisonPreferences
) -> OfferComparisonResult:
    first, second = _assessment(left, preferences), _assessment(right, preferences)
    weights = {
        "match": preferences.weights.match,
        "work_mode": preferences.weights.work_mode,
        "location": preferences.weights.location,
    }
    ranked = _ranking(first.scores, second.scores, weights)
    return OfferComparisonResult(
        preferences=preferences,
        first=first,
        second=second,
        scored_criteria=ranked.criteria,
        first_score=ranked.scores[0],
        second_score=ranked.scores[1],
        leader=ranked.leader,
        sensitivity=[_sensitivity(first.scores, second.scores, weights, key) for key in CRITERIA],
    )

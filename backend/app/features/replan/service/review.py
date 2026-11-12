"""Bilan hebdomadaire (SPEC F13, D99) : règles pures, sans base ni modèle.

Le bilan classe la semaine écoulée : en retard deux semaines de suite (plus de 30 %), en
retard, en avance ou dans les temps. Seuls les deux cas extrêmes proposent des options à January.
"""

from dataclasses import dataclass
from datetime import date
from math import floor

from app.agents.tools.study_schema import ReplanOption, ReviewState

LATE_THRESHOLD = 0.30  # part du temps prévu restée en retard ; « plus de », jamais « au moins »


@dataclass(frozen=True)
class WeekFacts:
    """Ce qui s'est passé pendant la semaine qui commence le lundi `week_start`."""

    week_start: date
    planned_minutes: int
    done_minutes: int
    tasks_planned: int
    tasks_done: int
    late_minutes: int  # minutes prévues cette semaine et restées à faire
    quiz_scores: list[int]
    done_ahead: int  # tâches de la semaine suivante déjà faites
    study_minutes: int
    captures: int


def late_ratio(facts: WeekFacts) -> float:
    """La part du temps prévu restée en retard ; rien de prévu : 0."""
    if facts.planned_minutes <= 0:
        return 0.0
    return facts.late_minutes / facts.planned_minutes


def classify(facts: WeekFacts, previous_ratio: float | None) -> ReviewState:
    """`late_twice` : plus de 30 % de retard et la semaine d'avant aussi ; `late` : un retard ;
    `ahead` : aucun retard et de l'avance prise ; sinon `on_track`."""
    ratio = late_ratio(facts)
    if ratio > LATE_THRESHOLD and previous_ratio is not None and previous_ratio > LATE_THRESHOLD:
        return "late_twice"
    if ratio > 0:
        return "late"
    return "ahead" if facts.done_ahead >= 1 else "on_track"


def options_for(state: ReviewState) -> tuple[ReplanOption, ...]:
    """Les choix offerts à January : réduire ou repousser s'il est très en retard, avancer ou
    approfondir s'il est en avance ; sinon rien à décider."""
    if state == "late_twice":
        return ("reduce_scope", "push_deadline")
    if state == "ahead":
        return ("advance", "deepen")
    return ()


def _duration(minutes: int) -> str:
    """`45 min`, `2 h`, `6 h 30`, `2 h 05`."""
    hours, rest = divmod(max(0, minutes), 60)
    if hours == 0:
        return f"{rest} min"
    return f"{hours} h" if rest == 0 else f"{hours} h {rest:02d}"


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}{'s' if n > 1 else ''}"


def _quiz(scores: list[int]) -> str:
    if not scores:
        return "aucun quiz"
    return f"quiz {floor(sum(scores) / len(scores) + 0.5)} %"


def review_text(facts: WeekFacts) -> str:
    """La ligne du bilan, sans modèle : « Semaine du 09/11 : 6 h 30 prévues, 3 h 15 faites,
    4 tâches sur 9, quiz 85 %, 2 h 10 d'étude, 3 captures. »"""
    parts = [
        f"{_duration(facts.planned_minutes)} prévues",
        f"{_duration(facts.done_minutes)} faites",
        f"{_count(facts.tasks_done, 'tâche')} sur {facts.tasks_planned}",
        _quiz(facts.quiz_scores),
        f"{_duration(facts.study_minutes)} d'étude",
        _count(facts.captures, "capture"),
    ]
    return f"Semaine du {facts.week_start:%d/%m} : {', '.join(parts)}."

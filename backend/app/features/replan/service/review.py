"""Weekly review (SPEC F13, D99): pure rules, with no database or model.

The review classifies the past week: late two weeks in a row (more than 30 %), late, ahead or
on track. Only the two extreme cases offer options to January.
"""

from dataclasses import dataclass
from datetime import date
from math import floor

from app.agents.tools.study_schema import ReplanOption, ReviewState

LATE_THRESHOLD = 0.30  # share of planned time left late; "more than", never "at least"


@dataclass(frozen=True)
class WeekFacts:
    """What happened during the week starting on Monday `week_start`."""

    week_start: date
    planned_minutes: int
    done_minutes: int
    tasks_planned: int
    tasks_done: int
    late_minutes: int  # minutes planned this week and still to do
    quiz_scores: list[int]
    done_ahead: int  # tasks of the following week already done
    study_minutes: int
    captures: int


def late_ratio(facts: WeekFacts) -> float:
    """The share of planned time left late; nothing planned: 0."""
    if facts.planned_minutes <= 0:
        return 0.0
    return facts.late_minutes / facts.planned_minutes


def classify(facts: WeekFacts, previous_ratio: float | None) -> ReviewState:
    """`late_twice`: more than 30 % late and the week before too; `late`: some delay;
    `ahead`: no delay and progress made ahead; otherwise `on_track`."""
    ratio = late_ratio(facts)
    if ratio > LATE_THRESHOLD and previous_ratio is not None and previous_ratio > LATE_THRESHOLD:
        return "late_twice"
    if ratio > 0:
        return "late"
    return "ahead" if facts.done_ahead >= 1 else "on_track"


def options_for(state: ReviewState) -> tuple[ReplanOption, ...]:
    """The choices offered to January: reduce or push back when far behind, advance or deepen
    when ahead; otherwise nothing to decide."""
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
        return "no quiz"
    return f"quiz {floor(sum(scores) / len(scores) + 0.5)} %"


def review_text(facts: WeekFacts) -> str:
    """The review line, with no model: "Week of 09/11: 6 h 30 planned, 3 h 15 done,
    4 tasks of 9, quiz 85 %, 2 h 10 of study, 3 captures."
    """
    parts = [
        f"{_duration(facts.planned_minutes)} planned",
        f"{_duration(facts.done_minutes)} done",
        f"{_count(facts.tasks_done, 'task')} of {facts.tasks_planned}",
        _quiz(facts.quiz_scores),
        f"{_duration(facts.study_minutes)} of study",
        _count(facts.captures, "capture"),
    ]
    return f"Week of {facts.week_start:%d/%m}: {', '.join(parts)}."

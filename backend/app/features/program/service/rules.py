"""La règle d'une semaine (SPEC 3.4) en un seul endroit (D86 §1, D88) : charge au plus 85 % du
budget, au moins une tâche de pratique, un quiz. Le brouillon du Stratège (`check_draft`), les
semaines rangées (`week_problems`) et les modifications de January (`editing.check_weeks`)
passent tous par `week_breaks`."""

from collections.abc import Sequence
from typing import Literal

from app.db.models.program import TaskType

WeekRule = Literal["week_over_budget", "week_needs_practice", "week_needs_quiz"]


def week_breaks(tasks: Sequence[tuple[int, TaskType]], cap_minutes: int) -> list[WeekRule]:
    """Règles cassées par les tâches `(minutes, type)` d'une semaine, dans cet ordre : charge,
    pratique, quiz."""
    breaks: list[WeekRule] = []
    if sum(minutes for minutes, _ in tasks) > cap_minutes:
        breaks.append("week_over_budget")
    if not any(kind == "pratiquer" for _, kind in tasks):
        breaks.append("week_needs_practice")
    if not any(kind == "quiz" for _, kind in tasks):
        breaks.append("week_needs_quiz")
    return breaks


def describe(rule: WeekRule, label: str, total: int, cap_minutes: int) -> str:
    """Phrase rendue au Stratège : « {label} : 735 min prévues, 714 au plus. »…"""
    if rule == "week_over_budget":
        return f"{label} : {total} min prévues, {cap_minutes} au plus."
    if rule == "week_needs_practice":
        return f"{label} : aucune tâche de pratique."
    return f"{label} : aucun quiz."

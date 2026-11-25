"""A week's rule (SPEC 3.4) in a single place (D86 §1, D88): load at most 85% of the budget, at
least one practice task, one quiz. The Strategist's draft (`check_draft`), the packed weeks
(`week_problems`) and January's edits (`editing.check_weeks`) all go through `week_breaks`.

Underload (D98) is not part of it: it is a Strategist-only rule (`check_draft`, then pulling
tasks forward at packing), January stays free to lighten a week."""

from collections.abc import Sequence
from typing import Literal

from app.db.models.program import TaskType

WeekRule = Literal["week_over_budget", "week_needs_practice", "week_needs_quiz"]
# Share of the cap that a Strategist week reaches at least, except the last (D98).
UNDERLOAD_SHARE = 0.6
# Title of the retry of a failed quiz, placed at D+2 (F9): never pulled forward by a packing.
# The French spellings are what programs stored before the switch to English contain.
RETRY_PREFIX = "Retake the quiz: "
RETRY_PREFIXES = (RETRY_PREFIX, "Refaire le quiz : ")
# "Continued" weeks and modules added for the tasks that do not fit.
SUITE_PREFIX = "Continued: "
SUITE_PREFIXES = (SUITE_PREFIX, "Suite : ")
SUITE_SUFFIX = " (continued)"
SUITE_SUFFIXES = (SUITE_SUFFIX, " (suite)")


def strip_suite_prefix(text: str) -> str:
    """`text` without a "Continued: " prefix (or its French form)."""
    for prefix in SUITE_PREFIXES:
        text = text.removeprefix(prefix)
    return text


def suite_theme(theme: str) -> str:
    """`theme` as the theme of a "Continued" week."""
    return f"{SUITE_PREFIX}{strip_suite_prefix(theme)}"


def suite_text(text: str) -> str:
    """`text` (objective, deliverable) as that of a "Continued" week."""
    return f"{strip_suite_suffix(text)}{SUITE_SUFFIX}"


def strip_suite_suffix(text: str) -> str:
    """`text` without a " (continued)" suffix (or its French form)."""
    for suffix in SUITE_SUFFIXES:
        text = text.removesuffix(suffix)
    return text


def is_retry(title: str, kind: TaskType) -> bool:
    return kind == "quiz" and title.startswith(RETRY_PREFIXES)


def floor_minutes(cap_minutes: int, share: float = UNDERLOAD_SHARE) -> int:
    """`share` of the cap rounded down, in integers (no float error):
    `floor_minutes(714)` = 428."""
    return cap_minutes * round(share * 100) // 100


def describe_underload(label: str, total: int, floor: int) -> str:
    """Describe a draft week below the target load."""
    return f"{label}: {total} min planned. Aim for at least {floor} min."


def week_breaks(tasks: Sequence[tuple[int, TaskType]], cap_minutes: int) -> list[WeekRule]:
    """Rules broken by the `(minutes, type)` tasks of a week, in this order: load, practice,
    quiz."""
    breaks: list[WeekRule] = []
    if sum(minutes for minutes, _ in tasks) > cap_minutes:
        breaks.append("week_over_budget")
    if not any(kind == "practice" for _, kind in tasks):
        breaks.append("week_needs_practice")
    if not any(kind == "quiz" for _, kind in tasks):
        breaks.append("week_needs_quiz")
    return breaks


def describe(rule: WeekRule, label: str, total: int, cap_minutes: int) -> str:
    """Describe the broken rule in a draft or scheduled week."""
    if rule == "week_over_budget":
        return f"{label}: {total} min planned. The limit is {cap_minutes} min."
    if rule == "week_needs_practice":
        return f"{label}: add at least one practice task."
    return f"{label}: add a quiz at the end of the week."

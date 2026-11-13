"""La règle d'une semaine (SPEC 3.4) en un seul endroit (D86 §1, D88) : charge au plus 85 % du
budget, au moins une tâche de pratique, un quiz. Le brouillon du Stratège (`check_draft`), les
semaines rangées (`week_problems`) et les modifications de January (`editing.check_weeks`)
passent tous par `week_breaks`.

La sous-charge (D98) n'en fait pas partie : c'est une règle du Stratège seulement (`check_draft`,
puis l'avance des tâches au rangement), January reste libre d'alléger une semaine."""

from collections.abc import Sequence
from typing import Literal

from app.db.models.program import TaskType

WeekRule = Literal["week_over_budget", "week_needs_practice", "week_needs_quiz"]
# Part du plafond qu'une semaine du Stratège atteint au moins, sauf la dernière (D98).
UNDERLOAD_SHARE = 0.6
# Titre du nouvel essai d'un quiz échoué, posé à J+2 (F9) : jamais avancé par un rangement.
RETRY_PREFIX = "Refaire le quiz : "


def is_retry(title: str, kind: TaskType) -> bool:
    return kind == "quiz" and title.startswith(RETRY_PREFIX)


def floor_minutes(cap_minutes: int, share: float = UNDERLOAD_SHARE) -> int:
    """`share` du plafond arrondi par défaut, en entiers (pas d'erreur flottante) :
    `floor_minutes(714)` = 428."""
    return cap_minutes * round(share * 100) // 100


def describe_underload(label: str, total: int, floor: int) -> str:
    """Phrase rendue au Stratège : « {label} : 125 min prévues, vise au moins 428 min. »"""
    return f"{label} : {total} min prévues, vise au moins {floor} min."


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

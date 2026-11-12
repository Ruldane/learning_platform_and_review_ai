"""Avance de tâches dans une semaine trop légère (D98), sur un type minimal partagé : des tâches
datées (minutes, jour, réservation). Le rangement d'un brouillon (`packing.pull_forward`, 60 %
du plafond) et la replanification sur les lignes en base (« avancer », 100 %) s'en servent ;
chacun applique ensuite les déplacements à ses propres données. Fonctions pures."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.features.program.service.budget import Budget
from app.features.program.service.rules import floor_minutes


@dataclass(frozen=True)
class Dated:
    """Une tâche rangée. `reserved` : le quiz qui ferme sa semaine ou sa pratique réservée,
    jamais avancés."""

    minutes: int
    day: date
    reserved: bool = False


@dataclass(frozen=True)
class WeekSlots:
    start: date
    tasks: Sequence[Dated]


@dataclass(frozen=True)
class Advance:
    """La tâche `index` de la semaine `source` passe le jour `day` de la semaine `source - 1`."""

    source: int
    index: int
    day: date


@dataclass
class _Receiver:
    """Semaine qui reçoit : charge, minutes par jour, curseur (jamais avant la dernière tâche
    non réservée : l'ordre des chapitres est gardé) et dernier jour (celui du quiz)."""

    load: int
    used: dict[date, int]
    cursor: date
    last_day: date

    @classmethod
    def of(cls, week: WeekSlots, kept: Sequence[Dated]) -> "_Receiver":
        used: dict[date, int] = {}
        for task in kept:
            used[task.day] = used.get(task.day, 0) + task.minutes
        free = [task.day for task in kept if not task.reserved]
        last = max((task.day for task in kept), default=week.start + timedelta(days=6))
        return cls(sum(used.values()), used, max(free, default=week.start), last)

    def place(self, task: Dated, budget: Budget) -> date | None:
        """Le premier jour, depuis le curseur, qui a la place de `task` sans passer le plafond."""
        if self.load + task.minutes > budget.cap_minutes:
            return None
        day = self.cursor
        while day <= self.last_day:
            if budget.day_capacity(day) - self.used.get(day, 0) >= task.minutes:
                self.used[day] = self.used.get(day, 0) + task.minutes
                self.load += task.minutes
                self.cursor = day
                return day
            day += timedelta(days=1)
        return None


def plan_advances(
    weeks: Sequence[WeekSlots], budget: Budget, *, floor_share: float
) -> list[Advance]:
    """Pour chaque semaine (sauf la dernière) sous `floor_share` × plafond, dans l'ordre : avance
    les tâches de la semaine suivante, dans leur ordre et jamais une réservée, sur les jours qui
    ont la place et jusqu'au jour du quiz, sans dépasser le plafond, tant que la semaine reste
    sous le seuil ; la première qui ne tient pas arrête l'avance. Une semaine vidée peut à son
    tour avancer des tâches de la suivante."""
    floor = floor_minutes(budget.cap_minutes, floor_share)
    left: list[list[tuple[int, Dated]]] = [list(enumerate(w.tasks)) for w in weeks]
    moves: list[Advance] = []
    for index in range(len(weeks) - 1):
        receiver = _Receiver.of(weeks[index], [task for _, task in left[index]])
        moved: set[int] = set()
        for rank, task in left[index + 1]:
            if receiver.load >= floor:
                break
            if task.reserved:
                continue
            day = receiver.place(task, budget)
            if day is None:
                break
            moves.append(Advance(index + 1, rank, day))
            moved.add(rank)
        left[index + 1] = [(rank, task) for rank, task in left[index + 1] if rank not in moved]
    return moves

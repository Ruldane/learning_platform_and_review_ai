"""Contrôles du brouillon à rendre au Stratège avant l'ordonnancement."""

from app.agents.tools.plan_schema import PlanDraft
from app.features.program.service.budget import Budget
from app.features.program.service.rules import (
    describe,
    describe_underload,
    floor_minutes,
    week_breaks,
)
from app.features.program.service.verbs import has_action_verb


def check_draft(draft: PlanDraft, budget: Budget) -> list[str]:
    """Une semaine sous 60 % du plafond doit être étoffée, sauf la dernière (D98)."""
    impossible: list[str] = []
    problems: list[str] = []
    cap, longest = budget.cap_minutes, budget.longest_day_minutes
    floor = floor_minutes(cap)
    for rank, week in enumerate(draft.weeks, start=1):
        label = f"Week {rank}"
        tasks = [task for module in week.modules for task in module.tasks]
        pairs = [(task.minutes, task.type) for task in tasks]
        total = sum(minutes for minutes, _ in pairs)
        for index, task in enumerate(tasks, start=1):
            if task.minutes > longest:
                impossible.append(
                    f"{label}, task {index}: {task.minutes} min, but the longest slot is "
                    f"{longest} min. Split the task into shorter steps."
                )
        problems += [describe(rule, label, total, cap) for rule in week_breaks(pairs, cap)]
        if rank < len(draft.weeks) and total < floor:
            problems.append(describe_underload(label, total, floor))
        problems.extend(
            f'{label}: start the task title "{task.title}" with an action verb.'
            for task in tasks
            if not has_action_verb(task.title)
        )
    return [*impossible, *problems]

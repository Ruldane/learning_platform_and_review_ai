"""Variables du prompt `replan` du Stratège (D105), tirées de l'instantané du contexte.

Le modèle ne voit que les références (`t12`, `m3`), jamais les ids (F7). Les titres des modules
et des tâches mêlent des textes du Stratège et de January : le plan est encadré par `untrusted()`
(17.4), comme le message et la note de January, et les compétences du déclencheur `gap` (tirées
d'offres d'emploi par l'Analyste, D123). L'objectif est son souhait : non encadré (D53 §5,
D84), comme pour le mode `plan`. Le bilan est écrit par le code."""

from typing import Any

from app.agents.nodes.strategist.plan_context import hours
from app.agents.nodes.strategist.replan_steps import OPTION_LABELS, STALE_NOTE
from app.agents.prompts.loader import untrusted
from app.agents.tools.replan_port import ReplanContext, TaskRef

_STATES = {
    "late_twice": "behind for two weeks in a row (over 30% of scheduled time)",
    "late": "behind schedule",
    "ahead": "ahead of schedule",
    "on_track": "on track",
}
_NO_RIGHT = "Write only `summary`. Omit additions and removals."
_RIGHTS = {
    "reduce_scope": (
        "Use `drop` with `t` references to remove the tasks least relevant to the goal. "
        "The code keeps at least one practice task and quiz each week."
    ),
    "deepen": (
        "Use `add` with an existing `module` reference starting with `m` to add tasks that "
        "develop the goal in depth within the weekly cap."
    ),
    "push_deadline": (
        "The code uses at most 60% of the cap in upcoming weeks and adds continuation weeks "
        "for the remaining work. " + _NO_RIGHT
    ),
    "advance": "The code brings upcoming tasks forward up to the weekly cap. " + _NO_RIGHT,
}
_GAP_RIGHT = (
    "Use `add` to create tasks only in module `m0` at the end of the program. In each "
    "task's title or completion criterion, name one of the skills exactly as listed below."
)
_DEFAULT_RIGHT = (
    "The code fits remaining tasks, including overdue tasks, within the budget. " + _NO_RIGHT
)


def _task_line(task: TaskRef) -> str:
    late = " — overdue" if task.late else ""
    return (
        f"- {task.ref}: {task.planned_date.isoformat()}, {task.title} ({task.type}, "
        f"{task.minutes} min, module {task.module_ref}){late}"
    )


def _plan(ctx: ReplanContext) -> str:
    lines = [f"Program: {ctx.title}", "", "Modules:"]
    lines += [f"- {m.ref}: {m.title} (skills: {', '.join(m.skills)})" for m in ctx.modules]
    lines += ["", "Remaining tasks:"]
    lines += [_task_line(t) for t in ctx.tasks] or ["- None"]
    return untrusted("\n".join(lines), "remaining plan")


def _skills(ctx: ReplanContext) -> str:
    listed = "\n".join(f"- {skill}" for skill in ctx.skills)
    return untrusted(listed, "skills from job postings") if listed else ""


def _rights(ctx: ReplanContext, option: str | None) -> str:
    if ctx.skills:
        return _GAP_RIGHT
    return _RIGHTS.get(option or "", _DEFAULT_RIGHT)


def replan_vars(
    ctx: ReplanContext, option: str | None, *, revision: int, note: str, stale: bool
) -> dict[str, Any]:
    budget, review = ctx.budget, ctx.review
    return {
        "goal": ctx.goal,
        "deadline": ctx.deadline.isoformat() if ctx.deadline else "none",
        "weekly_minutes": budget.weekly_minutes,
        "cap_minutes": budget.cap_minutes,
        "cap_hours": hours(budget.cap_minutes),
        "week_cap": ctx.week_cap_override,
        "review": review.text if review else "",
        "review_state": _STATES.get(review.state, review.state) if review else "",
        "option": OPTION_LABELS[option] if option else "",
        "rights": _rights(ctx, option),
        "trigger": "gap" if ctx.skills else "",
        "skills": _skills(ctx),
        "plan": _plan(ctx),
        "late_count": sum(1 for t in ctx.tasks if t.late),
        "message": untrusted(ctx.message, "message from January") if ctx.message else "",
        "note": untrusted(note, "note from January") if note else "",
        "stale": STALE_NOTE if stale else "",
        "revision": revision,
    }

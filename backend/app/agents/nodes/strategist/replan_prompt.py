"""Variables du prompt `replan` du Stratège (D105), tirées de l'instantané du contexte.

Le modèle ne voit que les références (`t12`, `m3`), jamais les ids (F7). Les titres des modules
et des tâches mêlent des textes du Stratège et de January : le plan est encadré par `untrusted()`
(17.4), comme le message et la note de January. L'objectif est son souhait : non encadré (D53 §5,
D84), comme pour le mode `plan`. Le bilan est écrit par le code."""

from typing import Any

from app.agents.nodes.strategist.plan_context import hours
from app.agents.nodes.strategist.replan_steps import OPTION_LABELS, STALE_NOTE
from app.agents.prompts.loader import untrusted
from app.agents.tools.replan_port import ReplanContext, TaskRef

_STATES = {
    "late_twice": "en retard deux semaines de suite (plus de 30 % du temps prévu)",
    "late": "en retard",
    "ahead": "en avance",
    "on_track": "dans les temps",
}
_NO_RIGHT = "Écris seulement le résumé (`summary`) : aucun retrait, aucun ajout."
_RIGHTS = {
    "reduce_scope": (
        "retirer des tâches (`drop`, par leur référence `t…`), jamais en ajouter : celles qui "
        "servent le moins l'objectif. Le code garde toujours une pratique et le quiz par semaine."
    ),
    "deepen": (
        "ajouter des tâches (`add`) dans un module existant (`module` : sa référence `m…`), jamais "
        "en retirer : ce qui approfondit l'objectif, sans alourdir une semaine au-delà du plafond."
    ),
    "push_deadline": (
        "aucun. Le code reporte ce qui ne tient pas en semaines « Suite » : l'échéance recule. "
        + _NO_RIGHT
    ),
    "advance": "aucun. Le code avance les tâches suivantes jusqu'au plafond. " + _NO_RIGHT,
}
_DEFAULT_RIGHT = (
    "aucun. Le code range les tâches à faire (retards compris) dans le budget. " + _NO_RIGHT
)


def _task_line(task: TaskRef) -> str:
    late = " — en retard" if task.late else ""
    return (
        f"- {task.ref} : {task.planned_date:%d/%m}, {task.title} ({task.type}, "
        f"{task.minutes} min, module {task.module_ref}){late}"
    )


def _plan(ctx: ReplanContext) -> str:
    lines = [f"Programme : {ctx.title}", "", "Modules :"]
    lines += [f"- {m.ref} : {m.title} (compétences : {', '.join(m.skills)})" for m in ctx.modules]
    lines += ["", "Tâches à faire :"]
    lines += [_task_line(t) for t in ctx.tasks] or ["- aucune"]
    return untrusted("\n".join(lines), "plan à faire")


def replan_vars(
    ctx: ReplanContext, option: str | None, *, revision: int, note: str, stale: bool
) -> dict[str, Any]:
    budget, review = ctx.budget, ctx.review
    return {
        "goal": ctx.goal,
        "deadline": ctx.deadline.strftime("%d/%m/%Y") if ctx.deadline else "aucune",
        "weekly_minutes": budget.weekly_minutes,
        "cap_minutes": budget.cap_minutes,
        "cap_hours": hours(budget.cap_minutes),
        "week_cap": ctx.week_cap_override,
        "review": review.text if review else "",
        "review_state": _STATES.get(review.state, review.state) if review else "",
        "option": OPTION_LABELS[option] if option else "",
        "rights": _RIGHTS.get(option or "", _DEFAULT_RIGHT),
        "plan": _plan(ctx),
        "late_count": sum(1 for t in ctx.tasks if t.late),
        "message": untrusted(ctx.message, "message de January") if ctx.message else "",
        "note": untrusted(note, "note de January") if note else "",
        "stale": STALE_NOTE if stale else "",
        "revision": revision,
    }

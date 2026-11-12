"""Règles du programme (SPEC 3.4) : acquis, pratique et quiz chaque semaine, 85 % du budget.

Le Stratège propose un brouillon (`PlanDraft`) ; ce module le vérifie (`check_draft`), l'allège
des acquis de January (`apply_known`), le complète (`ensure_week_rules`) et le range sur le
calendrier (`schedule`). Rien ici n'écrit en base ni n'appelle un modèle.
"""

from collections.abc import Sequence
from datetime import date, timedelta

from app.agents.tools.plan_schema import KnownSkills, ModuleDraft, PlanDraft, TaskDraft, WeekDraft
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.packing import (
    Entry,
    NoRoom,
    Placement,
    ScheduledPlan,
    ScheduledTask,
    ScheduledWeek,
    final_quiz,
    first_practice,
    pack_week,
)
from app.features.program.service.rules import describe, week_breaks
from app.features.program.service.verbs import ACTION_VERBS, has_action_verb

# Types de l'ordonnancement et verbes d'action : réexportés pour les autres modules du programme.
__all__ = ["ACTION_VERBS", "ScheduledPlan", "ScheduledTask", "ScheduledWeek"]

REVIEW_MINUTES = 20
PRACTICE_MINUTES = 45
QUIZ_MINUTES = 20
MAX_WEEKS = 52
MONDAY = 0

REVIEW_PREFIX = "Réviser : "
REVIEW_CRITERION = "Relire la fiche et répondre aux questions d'auto-évaluation"
_PRACTICE_CRITERION = "Produire un résultat que l'on peut montrer et expliquer"
_QUIZ_CRITERION = "Répondre à toutes les questions puis relire les erreurs"
_SKILLED = ("valide", "prouve")


class PlanningImpossible(AppError):
    def __init__(
        self, message: str = "Budget hebdomadaire trop faible pour une pratique et un quiz."
    ) -> None:
        super().__init__("planning_impossible", message, status_code=422)


def next_monday(today: date) -> date:
    """`today` si c'est un lundi, sinon le lundi suivant."""
    return today + timedelta(days=(MONDAY - today.weekday()) % 7)


def is_review(task: TaskDraft) -> bool:
    """Révision d'un acquis (produite par `apply_known`) : tâche « déjà acquise »."""
    return (
        task.type == "lire"
        and task.minutes == REVIEW_MINUTES
        and task.title.startswith(REVIEW_PREFIX)
        and task.done_criterion == REVIEW_CRITERION
    )


def _week_tasks(week: WeekDraft) -> list[TaskDraft]:
    return [task for module in week.modules for task in module.tasks]


def check_draft(draft: PlanDraft, budget: Budget) -> list[str]:
    """Problèmes du brouillon, en français, à rendre au Stratège pour qu'il corrige."""
    problems: list[str] = []
    for rank, week in enumerate(draft.weeks, start=1):
        tasks = _week_tasks(week)
        pairs = [(task.minutes, task.type) for task in tasks]
        total, cap = sum(minutes for minutes, _ in pairs), budget.cap_minutes
        problems += [
            describe(rule, f"Semaine {rank}", total, cap) for rule in week_breaks(pairs, cap)
        ]
        problems.extend(
            f"Semaine {rank} : le titre « {task.title} » ne commence pas par un verbe d'action."
            for task in tasks
            if not has_action_verb(task.title)
        )
    return problems


def _review_of(module: ModuleDraft) -> ModuleDraft:
    task = TaskDraft(
        title=(REVIEW_PREFIX + module.title)[:120],
        type="lire",
        minutes=REVIEW_MINUTES,
        done_criterion=REVIEW_CRITERION,
    )
    return module.model_copy(update={"tasks": [task]})


def apply_known(draft: PlanDraft, known: KnownSkills) -> tuple[PlanDraft, list[str]]:
    """Saute les modules acquis (valide, prouve) ; réduit les autres à une révision de 20 min.

    Un module n'est concerné que si TOUTES ses compétences sont connues. Une semaine dont tous
    les modules sont sautés disparaît. Rend le brouillon allégé et les titres des modules sautés.
    """
    skipped: list[str] = []
    weeks: list[WeekDraft] = []
    for week in draft.weeks:
        modules: list[ModuleDraft] = []
        for module in week.modules:
            levels = [known.get(normalize_skill_name(skill)) for skill in module.skills]
            if not module.skills or None in levels:
                modules.append(module)
            elif all(level in _SKILLED for level in levels):
                skipped.append(module.title)
            else:
                modules.append(_review_of(module))
        if modules:
            weeks.append(week.model_copy(update={"modules": modules}))
    return draft.model_copy(update={"weeks": weeks}), skipped


def _quizzes_last(tasks: list[TaskDraft]) -> list[TaskDraft]:
    return [t for t in tasks if t.type != "quiz"] + [t for t in tasks if t.type == "quiz"]


def ensure_week_rules(week: WeekDraft, rank: int) -> WeekDraft:
    """Ajoute la pratique et le quiz manquants (dernier module) ; les quiz passent en dernier."""
    modules = [m.model_copy(update={"tasks": _quizzes_last(m.tasks)}) for m in week.modules]
    if not modules:
        modules = [
            ModuleDraft.model_construct(
                title=week.theme, skills=[week.theme], prerequisites=[], tasks=[]
            )
        ]
    last = modules[-1]
    body = [t for t in last.tasks if t.type != "quiz"]
    quizzes = [t for t in last.tasks if t.type == "quiz"]
    tasks = [task for module in modules for task in module.tasks]
    if not any(task.type == "pratiquer" for task in tasks):
        body.append(
            TaskDraft(
                title=f"Pratiquer : {week.theme}"[:120],
                type="pratiquer",
                minutes=PRACTICE_MINUTES,
                done_criterion=_PRACTICE_CRITERION,
            )
        )
    if not any(task.type == "quiz" for task in tasks):
        quizzes.append(
            TaskDraft(
                title=f"Faire le quiz de la semaine {rank}",
                type="quiz",
                minutes=QUIZ_MINUTES,
                done_criterion=_QUIZ_CRITERION,
            )
        )
    modules[-1] = last.model_copy(update={"tasks": body + quizzes})
    return week.model_copy(update={"modules": modules})


def week_problems(
    tasks: Sequence[tuple[date, int, TaskType]], week_start: date, budget: Budget
) -> list[str]:
    """Règles vérifiées à chaque modification d'une semaine : charge, pratique, quiz."""
    label = f"Semaine du {week_start:%d/%m}"
    pairs = [(minutes, kind) for _, minutes, kind in tasks]
    total, cap = sum(minutes for minutes, _ in pairs), budget.cap_minutes
    return [describe(rule, label, total, cap) for rule in week_breaks(pairs, cap)]


def _entries(week: WeekDraft, week_index: int) -> list[Entry]:
    return [
        Entry(task, (week_index, module_index, task_index))
        for module_index, module in enumerate(week.modules)
        for task_index, task in enumerate(module.tasks)
    ]


def _suite_week(last: WeekDraft) -> WeekDraft:
    """Semaine ajoutée pour les tâches qui ne tiennent pas : thème et livrable repris."""
    theme = last.theme.removeprefix("Suite : ")
    module = ModuleDraft.model_construct(
        title=f"Suite : {theme}"[:120], skills=[theme[:120]], prerequisites=[], tasks=[]
    )
    return last.model_copy(
        update={
            "theme": f"Suite : {theme}"[:120],
            "objective": f"{last.objective.removesuffix(' (suite)')} (suite)"[:300],
            "deliverable": f"{last.deliverable.removesuffix(' (suite)')} (suite)"[:300],
            "modules": [module],
        }
    )


def _build_week(
    rank: int,
    week: WeekDraft,
    placed: list[Placement],
    start: date,
    sources: list[WeekDraft],
    seen: set[tuple[int, int]],
) -> ScheduledWeek:
    keys = sorted({p.entry.origin[:2] for p in placed})
    modules: list[ModuleDraft] = []
    for week_index, module_index in keys:
        source = sources[week_index].modules[module_index]
        title = (
            f"{source.title[:112]} (suite)" if (week_index, module_index) in seen else source.title
        )
        tasks = [p.entry.task for p in placed if p.entry.origin[:2] == (week_index, module_index)]
        modules.append(source.model_copy(update={"title": title, "tasks": tasks}))
    seen.update(keys)
    tasks_out = [
        ScheduledTask(
            title=p.entry.task.title,
            type=p.entry.task.type,
            minutes=p.entry.task.minutes,
            done_criterion=p.entry.task.done_criterion,
            planned_date=p.day,
            already_known=is_review(p.entry.task),
            module_index=keys.index(p.entry.origin[:2]),
        )
        for p in placed
    ]
    return ScheduledWeek(
        rank=rank,
        theme=week.theme,
        objective=week.objective,
        deliverable=week.deliverable,
        start_date=start,
        modules=modules,
        tasks=tasks_out,
        load_minutes=sum(t.minutes for t in tasks_out),
    )


def _check_fits(weeks: list[WeekDraft], budget: Budget) -> None:
    """Refuse d'emblée ce qu'aucune semaine ne pourrait contenir (budget trop faible)."""
    longest = max(budget.weekday_minutes, budget.weekend_minutes)
    for week in weeks:
        entries = _entries(week, 0)
        reserved = [e for e in (final_quiz(entries), first_practice(entries)) if e is not None]
        if sum(e.task.minutes for e in reserved) > budget.cap_minutes:
            raise PlanningImpossible()
        for task in _week_tasks(week):
            if task.minutes > longest:
                raise PlanningImpossible(
                    f"Aucun jour n'a assez de temps pour une tâche de {task.minutes} minutes."
                )


def schedule(draft: PlanDraft, budget: Budget, known: KnownSkills, start: date) -> ScheduledPlan:
    """Range le brouillon sur le calendrier : jamais plus de 85 % du budget par semaine.

    Ce qui ne tient pas passe à la semaine suivante ; des semaines « Suite » sont ajoutées tant
    qu'il reste des tâches (52 semaines au plus). `start` est le premier jour (un lundi).
    """
    reduced, skipped = apply_known(draft, known)
    if not reduced.weeks:
        return ScheduledPlan([], skipped, 0)
    sources = [ensure_week_rules(w, rank) for rank, w in enumerate(reduced.weeks, start=1)]
    original = len(sources)
    _check_fits(sources, budget)
    weeks: list[ScheduledWeek] = []
    carried: list[Entry] = []
    seen: set[tuple[int, int]] = set()
    moved = 0
    while len(weeks) < original or carried:
        index = len(weeks)
        if index >= MAX_WEEKS:
            raise PlanningImpossible("Le programme dépasse 52 semaines avec ce budget.")
        if index >= original:
            sources.append(ensure_week_rules(_suite_week(sources[original - 1]), index + 1))
        first_day = start + timedelta(days=7 * index)
        try:
            packing = pack_week(carried, _entries(sources[index], index), budget, first_day)
        except NoRoom:
            raise PlanningImpossible() from None
        if index >= original and not any(p.entry.origin[0] < index for p in packing.placed):
            raise PlanningImpossible()
        moved += sum(1 for p in packing.placed if p.entry.origin[0] != index)
        weeks.append(
            _build_week(index + 1, sources[index], packing.placed, first_day, sources, seen)
        )
        carried = packing.deferred
    return ScheduledPlan(weeks, skipped, moved)

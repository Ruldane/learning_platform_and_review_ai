"""Program rules (SPEC 3.4): learned items, practice and quiz every week, 85% of the budget.

The Strategist proposes a draft (`PlanDraft`); this module checks it (`check_draft`), lightens
it with January's known skills (`apply_known`), completes it (`ensure_week_rules`) and places
it on the calendar (`schedule`). Nothing here writes to the database or calls a model.
"""

from collections.abc import Sequence
from datetime import date, timedelta

from app.agents.tools.plan_schema import KnownSkills, ModuleDraft, PlanDraft, TaskDraft, WeekDraft
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.draft_checks import check_draft
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
    pull_forward,
)
from app.features.program.service.rules import (
    SUITE_SUFFIX,
    UNDERLOAD_SHARE,
    describe,
    strip_suite_prefix,
    suite_text,
    suite_theme,
    week_breaks,
)
from app.features.program.service.verbs import ACTION_VERBS, review_subject

# Scheduling types, action verbs and underload share: re-exported.
__all__ = [
    "ACTION_VERBS",
    "UNDERLOAD_SHARE",
    "ScheduledPlan",
    "ScheduledTask",
    "ScheduledWeek",
    "check_draft",
]

REVIEW_MINUTES = 20
PRACTICE_MINUTES = 45
QUIZ_MINUTES = 20
MAX_WEEKS = 52
MONDAY = 0

REVIEW_PREFIX = "Review: "
REVIEW_CRITERION = "Re-read the card and answer the self-assessment questions"
# The French spellings are what programs stored before the switch to English contain.
_LEGACY_REVIEW = ("Réviser : ", "Relire la fiche et répondre aux questions d'auto-évaluation")
_PRACTICE_CRITERION = "Produce a result you can show and explain"
_QUIZ_CRITERION = "Answer all the questions then re-read the mistakes"
_SKILLED = ("validated", "proven")


class PlanningImpossible(AppError):
    def __init__(
        self, message: str = "Your weekly budget is too low for a practice task and a quiz."
    ) -> None:
        super().__init__("planning_impossible", message, status_code=422)


def next_monday(today: date) -> date:
    """`today` if it is a Monday, otherwise the following Monday."""
    return today + timedelta(days=(MONDAY - today.weekday()) % 7)


def is_review(task: TaskDraft) -> bool:
    """Review of a learned item (produced by `apply_known`): an "already known" task."""
    return (
        task.type == "read"
        and task.minutes == REVIEW_MINUTES
        and (
            (task.title.startswith(REVIEW_PREFIX) and task.done_criterion == REVIEW_CRITERION)
            or (
                task.title.startswith(_LEGACY_REVIEW[0])
                and task.done_criterion == _LEGACY_REVIEW[1]
            )
        )
    )


def _week_tasks(week: WeekDraft) -> list[TaskDraft]:
    return [task for module in week.modules for task in module.tasks]


def _review_of(module: ModuleDraft) -> ModuleDraft:
    task = TaskDraft(
        title=(REVIEW_PREFIX + review_subject(module.title))[:120],
        type="read",
        minutes=REVIEW_MINUTES,
        done_criterion=REVIEW_CRITERION,
    )
    return module.model_copy(update={"tasks": [task]})


def apply_known(draft: PlanDraft, known: KnownSkills) -> tuple[PlanDraft, list[str]]:
    """Skips the known modules (validated, proven); reduces the others to a 20 min review.

    A module is only concerned if ALL its skills are known. A week whose modules are all
    skipped disappears. Returns the lightened draft and the titles of the skipped modules.
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
    """Adds the missing practice and quiz (last module); quizzes go last."""
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
    if not any(task.type == "practice" for task in tasks):
        body.append(
            TaskDraft(
                title=f"Pratiquer : {week.theme}"[:120],
                type="practice",
                minutes=PRACTICE_MINUTES,
                done_criterion=_PRACTICE_CRITERION,
            )
        )
    if not any(task.type == "quiz" for task in tasks):
        quizzes.append(
            TaskDraft(
                title=f"Take the week {rank} quiz",
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
    """Rules checked at each edit of a week: load, practice, quiz."""
    label = f"Week of {week_start:%d/%m}"
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
    """Week added for the tasks that do not fit: theme and deliverable carried over."""
    theme = strip_suite_prefix(last.theme)
    module = ModuleDraft.model_construct(
        title=suite_theme(theme)[:120], skills=[theme[:120]], prerequisites=[], tasks=[]
    )
    return last.model_copy(
        update={
            "theme": suite_theme(theme)[:120],
            "objective": suite_text(last.objective)[:300],
            "deliverable": suite_text(last.deliverable)[:300],
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
            f"{source.title[:112]}{SUITE_SUFFIX}"
            if (week_index, module_index) in seen
            else source.title
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
        stage=week.stage,
        rationale=week.rationale,
    )


def _check_fits(weeks: list[WeekDraft], budget: Budget) -> None:
    """Refuses at once what no week could hold (budget too low)."""
    longest = budget.longest_day_minutes
    for week in weeks:
        entries = _entries(week, 0)
        reserved = [e for e in (final_quiz(entries), first_practice(entries)) if e is not None]
        if sum(e.task.minutes for e in reserved) > budget.cap_minutes:
            raise PlanningImpossible()
        for task in _week_tasks(week):
            if task.minutes > longest:
                raise PlanningImpossible(
                    f"No day has enough time for a {task.minutes}-minute task."
                )


def schedule(draft: PlanDraft, budget: Budget, known: KnownSkills, start: date) -> ScheduledPlan:
    """Places the draft on the calendar: never more than 85% of the budget per week.

    What does not fit moves to the next week; "Continued" weeks are added as long as tasks
    remain (52 weeks at most). `start` is the first day (a Monday). A week under 60% of the cap,
    except the last, then pulls tasks forward from the next one.
    """
    reduced, skipped = apply_known(draft.with_chapter_indices(), known)
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
            raise PlanningImpossible("The program exceeds 52 weeks with this budget.")
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
    return ScheduledPlan(pull_forward(weeks, budget, floor_share=UNDERLOAD_SHARE), skipped, moved)

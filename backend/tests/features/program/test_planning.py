import random
from datetime import date

import pytest

from app.agents.tools.plan_schema import PlanDraft
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.planning import (
    PlanningImpossible,
    ScheduledPlan,
    apply_known,
    check_draft,
    ensure_week_rules,
    is_review,
    next_monday,
    schedule,
    week_problems,
)
from tests.support.program import MONDAY, full_week, module, plan, task, week


def _known_draft() -> PlanDraft:
    first = module("Bases de Python", [task("Lire la doc")], skills=["Python"])
    second = module(
        "Manipuler des données avec pandas",
        [task("Lire la doc de pandas"), task("Pratiquer sur un jeu", "pratiquer", 60)],
        skills=["Pandas"],
    )
    return plan([week("Données", [first, second])])


def test_check_draft_reports_week_over_cap(budget: Budget) -> None:
    reads = [task("Lire un chapitre", minutes=120)] * 6
    extra = [task("Pratiquer le sujet", "pratiquer", 40), task("Faire le quiz", "quiz", 20)]
    draft = plan([week("Gros", [module("Beaucoup", reads + extra)])])
    assert "Semaine 1 : 780 min prévues, 714 au plus." in check_draft(draft, budget)


def test_check_draft_reports_missing_practice_quiz_and_verb(budget: Budget) -> None:
    draft = plan([week("Bases", [module("Intro", [task("Théorie des graphes", "lire")])])])
    problems = check_draft(draft, budget)
    assert "Semaine 1 : aucune tâche de pratique." in problems
    assert "Semaine 1 : aucun quiz." in problems
    assert any("Théorie des graphes" in p and "verbe d'action" in p for p in problems)


def test_check_draft_accepts_a_good_week(budget: Budget) -> None:
    assert check_draft(plan([full_week("Bases", [30, 30])]), budget) == []


def test_action_verbs_by_ending_or_list(budget: Budget) -> None:
    titles = ["Lire la doc", "Regarder la vidéo", "Écrire un test", "Comprendre la boucle"]
    titles += ["Voir les cas", "Fais un schéma", "Savoir lire"]
    tasks = [task(t) for t in titles]
    tasks += [task("Pratiquer le sujet", "pratiquer"), task("Faire le quiz", "quiz")]
    assert check_draft(plan([week("Bases", [module("Intro", tasks)])]), budget) == []


def test_valide_module_is_skipped_declare_is_reduced_to_review() -> None:
    draft, skipped = apply_known(_known_draft(), {"python": "valide", "pandas": "declare"})
    assert skipped == ["Bases de Python"]
    review = draft.weeks[0].modules[0].tasks
    assert [(t.title, t.minutes, t.type) for t in review] == [
        ("Réviser : Manipuler des données avec pandas", 20, "lire")
    ]
    assert is_review(review[0]) and len(draft.weeks[0].modules) == 1


def test_proved_and_in_progress_levels() -> None:
    _, skipped = apply_known(_known_draft(), {"python": "prouve", "pandas": "valide"})
    assert skipped == ["Bases de Python", "Manipuler des données avec pandas"]
    draft, skipped = apply_known(_known_draft(), {"python": "en_cours", "pandas": "en_cours"})
    assert skipped == [] and all(is_review(m.tasks[0]) for m in draft.weeks[0].modules)


def test_module_with_one_unknown_skill_is_kept_whole() -> None:
    mixed = module("Mixte", [task("Lire un chapitre")], skills=["Python", "Rust"])
    draft, skipped = apply_known(plan([week("Mixte", [mixed])]), {"python": "prouve"})
    assert skipped == [] and draft.weeks[0].modules[0].tasks == mixed.tasks


def test_known_skill_names_are_matched_after_normalization() -> None:
    m = module("Réseaux", [task("Lire un cours")], skills=["  Réseaux de Neurones."])
    _, skipped = apply_known(plan([week("Intelligence", [m])]), {"reseaux de neurones": "valide"})
    assert skipped == ["Réseaux"]


def test_week_with_every_module_skipped_disappears() -> None:
    draft = plan(
        [week("Alpha", [module("Uno", [task("Lire un")], skills=["a"])]), full_week("Beta", [30])]
    )
    reduced, skipped = apply_known(draft, {"a": "valide"})
    assert skipped == ["Uno"] and [w.theme for w in reduced.weeks] == ["Beta"]


def test_week_gets_practice_and_ends_with_quiz() -> None:
    bare = week("Bases", [module("Intro", [task("Lire un"), task("Faire un test", "quiz")])])
    tasks = ensure_week_rules(bare, 3).modules[-1].tasks
    assert [(t.title, t.type, t.minutes) for t in tasks] == [
        ("Lire un", "lire", 30),
        ("Pratiquer : Bases", "pratiquer", 45),
        ("Faire un test", "quiz", 30),
    ]
    added = ensure_week_rules(week("Bases", [module("Intro", [task("Lire un")])]), 3)
    last = added.modules[-1].tasks[-2:]
    assert [(t.title, t.type, t.minutes) for t in last] == [
        ("Pratiquer : Bases", "pratiquer", 45),
        ("Faire le quiz de la semaine 3", "quiz", 20),
    ]


def test_ensure_week_rules_is_idempotent_and_keeps_input() -> None:
    bare = week("Bases", [module("Intro", [task("Lire un")])])
    once = ensure_week_rules(bare, 1)
    assert ensure_week_rules(once, 1) == once
    assert len(bare.modules[0].tasks) == 1


def test_quiz_inside_a_module_moves_after_its_other_tasks() -> None:
    tasks = [task("Faire le quiz", "quiz"), task("Lire un"), task("Pratiquer", "pratiquer")]
    fixed = ensure_week_rules(week("Bases", [module("Intro", tasks)]), 1)
    assert [t.type for t in fixed.modules[0].tasks] == ["lire", "pratiquer", "quiz"]


def test_schedule_never_exceeds_85_percent(budget: Budget) -> None:
    drafts = [
        plan([full_week("Alpha", [120] * 8), full_week("Beta", [120] * 8)]),
        plan(
            [full_week("Alpha", [30, 60]), full_week("Beta", [120] * 3), full_week("Gamma", [15])]
        ),
        plan([week("Nulle", [module("Nulle", [task("Lire un", minutes=90)] * 9)])]),
    ]
    for draft in drafts:
        result = schedule(draft, budget, {}, MONDAY)
        for w in result.weeks:
            assert w.load_minutes <= 714
            assert w.load_minutes == sum(t.minutes for t in w.tasks)


def test_overflow_moves_tasks_to_next_week_and_appends_a_week(budget: Budget) -> None:
    result = schedule(plan([full_week("Gros", [120] * 8)]), budget, {}, MONDAY)
    assert result.moved_tasks > 0 and len(result.weeks) == 2
    second = result.weeks[1]
    assert second.theme == "Suite : Gros" and second.objective.endswith("(suite)")
    assert {"pratiquer", "quiz"} <= {t.type for t in second.tasks}
    assert second.start_date == date(2026, 11, 23)
    assert second.modules[0].title == "Module Gros (suite)"
    assert sum(1 for w in result.weeks for t in w.tasks if t.title.startswith("Lire")) == 8


def test_overflow_keeps_task_order(budget: Budget) -> None:
    result = schedule(plan([full_week("Gros", [120] * 8)]), budget, {}, MONDAY)
    reads = [t for w in result.weeks for t in w.tasks if t.title.startswith("Lire")]
    assert [t.title for t in reads] == [f"Lire le chapitre {i}" for i in range(1, 9)]
    assert reads == sorted(reads, key=lambda t: t.planned_date)


def test_quiz_is_last_task_of_each_week(budget: Budget) -> None:
    draft = plan([full_week("Gros", [120] * 8), full_week("Beta", [60, 60])])
    for w in schedule(draft, budget, {}, MONDAY).weeks:
        assert w.tasks[-1].type == "quiz"
        assert w.tasks[-1].planned_date == max(t.planned_date for t in w.tasks)


def test_tasks_stay_in_their_week_and_never_on_sunday(budget: Budget) -> None:
    result = schedule(plan([full_week("Gros", [120] * 8)] * 2), budget, {}, MONDAY)
    for w in result.weeks:
        per_day: dict[date, int] = {}
        for t in w.tasks:
            assert 0 <= (t.planned_date - w.start_date).days <= 6
            assert t.planned_date.weekday() != 6
            per_day[t.planned_date] = per_day.get(t.planned_date, 0) + t.minutes
        assert all(m <= budget.day_capacity(d) for d, m in per_day.items())


def test_module_indexes_point_into_the_week_modules(budget: Budget) -> None:
    one = module("Uno", [task("Lire un", minutes=60)])
    two = module("Dos", [task("Lire deux", minutes=60)])
    w = schedule(plan([week("Binôme", [one, two])]), budget, {}, MONDAY).weeks[0]
    by_module = {t.title: w.modules[t.module_index].title for t in w.tasks}
    assert by_module["Lire un"] == "Uno" and by_module["Lire deux"] == "Dos"
    assert by_module["Faire le quiz de la semaine 1"] == "Dos"


def test_known_skills_are_skipped_reviewed_and_flagged(budget: Budget) -> None:
    result = schedule(_known_draft(), budget, {"python": "valide", "pandas": "declare"}, MONDAY)
    assert result.skipped_modules == ["Bases de Python"]
    known = [t for t in result.weeks[0].tasks if t.already_known]
    assert [(t.title, t.minutes) for t in known] == [
        ("Réviser : Manipuler des données avec pandas", 20)
    ]


def test_everything_known_gives_an_empty_plan(budget: Budget) -> None:
    result = schedule(_known_draft(), budget, {"python": "prouve", "pandas": "prouve"}, MONDAY)
    skipped = ["Bases de Python", "Manipuler des données avec pandas"]
    assert result == ScheduledPlan([], skipped, 0)


def test_tiny_budget_is_planning_impossible() -> None:
    tiny = Budget(weekday_minutes=4, weekend_minutes=8)  # 28 min par semaine
    with pytest.raises(PlanningImpossible) as info:
        schedule(plan([full_week("Alpha", [15])]), tiny, {}, MONDAY)
    assert info.value.code == "planning_impossible" and info.value.status_code == 422
    assert info.value.message == "Budget hebdomadaire trop faible pour une pratique et un quiz."


def test_task_longer_than_any_day_is_impossible() -> None:
    narrow = Budget(weekday_minutes=60, weekend_minutes=60)
    with pytest.raises(PlanningImpossible):
        schedule(plan([full_week("Alpha", [90])]), narrow, {}, MONDAY)


def test_more_than_52_weeks_is_impossible(budget: Budget) -> None:
    year = plan([full_week(f"Semaine {i}", [120] * 6) for i in range(52)])
    with pytest.raises(PlanningImpossible, match="52 semaines"):
        schedule(year, budget, {}, MONDAY)


def test_next_monday() -> None:
    assert next_monday(date(2026, 11, 12)) == date(2026, 11, 16)
    assert next_monday(date(2026, 11, 16)) == date(2026, 11, 16)
    assert next_monday(date(2026, 11, 22)) == date(2026, 11, 23)


def test_week_problems(budget: Budget) -> None:
    day = date(2026, 11, 16)
    ok = [(day, 100, "lire"), (day, 45, "pratiquer"), (day, 20, "quiz")]
    assert week_problems(ok, MONDAY, budget) == []
    over = [(day, 700, "lire"), (day, 15, "pratiquer"), (day, 20, "quiz")]
    assert week_problems(over, MONDAY, budget) == [
        "Semaine du 16/11 : 735 min prévues, 714 au plus."
    ]
    bare = week_problems([(day, 30, "lire")], MONDAY, budget)
    assert bare == [
        "Semaine du 16/11 : aucune tâche de pratique.",
        "Semaine du 16/11 : aucun quiz.",
    ]


def test_random_drafts_keep_every_rule(budget: Budget) -> None:
    rng = random.Random(83)
    kinds: list[TaskType] = ["lire", "regarder", "pratiquer", "quiz", "projet"]
    for _ in range(40):
        weeks = []
        for index in range(rng.randint(1, 6)):
            tasks = [
                task(f"Lire le point {n}", rng.choice(kinds), rng.randrange(15, 121, 15))
                for n in range(rng.randint(1, 12))
            ]
            weeks.append(week(f"Thème {index}", [module(f"Module {index}", tasks)]))
        result = schedule(plan(weeks), budget, {}, MONDAY)
        placed = sum(len(w.tasks) for w in result.weeks)
        assert placed >= sum(len(w.modules[0].tasks) for w in weeks)
        for w in result.weeks:
            per_day: dict[date, int] = {}
            for t in w.tasks:
                per_day[t.planned_date] = per_day.get(t.planned_date, 0) + t.minutes
            assert w.load_minutes <= budget.cap_minutes
            assert all(m <= budget.day_capacity(d) for d, m in per_day.items())
            assert w.tasks[-1].type == "quiz" and any(t.type == "pratiquer" for t in w.tasks)
            assert w.tasks[-1].planned_date == max(per_day)

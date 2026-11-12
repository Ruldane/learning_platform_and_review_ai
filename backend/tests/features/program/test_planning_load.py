"""Reliquat de la phase 4 (D98) : semaine trop légère signalée au Stratège et comblée au
rangement, titre de révision sans préfixe doublé."""

import pytest

from app.agents.tools.plan_schema import PlanDraft
from app.features.program.service.budget import Budget
from app.features.program.service.planning import (
    UNDERLOAD_SHARE,
    apply_known,
    check_draft,
    is_review,
    schedule,
)
from tests.support.program import MONDAY, full_week, module, plan, task, week

UNDERLOAD = "Semaine 1 : 125 min prévues, vise au moins 428 min."


def _draft_with_module(title: str, skills: list[str]) -> PlanDraft:
    return plan([week("Bases", [module(title, [task("Lire la doc")], skills=skills)])])


def _light_then_full() -> PlanDraft:
    light = [task("Lire un chapitre", minutes=60)]
    light += [task("Pratiquer le sujet", "pratiquer", 45), task("Faire le quiz", "quiz", 20)]
    return plan([week("Léger", [module("Module Léger", light)]), full_week("Plein", [120] * 5)])


def _two_weeks_first_known() -> PlanDraft:
    known = module("Bases de Python", [task("Lire la doc", minutes=60)], skills=["Python"])
    return plan([week("Bases", [known]), full_week("Projet", [120] * 5)])


@pytest.mark.parametrize(
    "title",
    [
        "Réviser Python appliqué",
        "Réviser : Python appliqué",
        "réviser: Python appliqué",
        "REVISER Python appliqué",
        "Révision de Python appliqué",
        "Revision de : Python appliqué",
        "Revoir Python appliqué",
        "  Revoir : Python appliqué",
    ],
)
def test_review_title_is_not_doubled(title: str) -> None:
    draft, _ = apply_known(_draft_with_module(title, ["python"]), {"python": "declare"})
    review = draft.weeks[0].modules[0].tasks[0]
    assert review.title == "Réviser : Python appliqué" and is_review(review)


@pytest.mark.parametrize("title", ["Révisions générales", "Revoiture", "Réviser"])
def test_review_title_keeps_other_titles(title: str) -> None:
    draft, _ = apply_known(_draft_with_module(title, ["python"]), {"python": "declare"})
    assert draft.weeks[0].modules[0].tasks[0].title == f"Réviser : {title}"


def test_check_draft_reports_underloaded_week(budget: Budget) -> None:
    assert UNDERLOAD_SHARE == 0.6
    problems = check_draft(_light_then_full(), budget)
    assert problems == [UNDERLOAD]


def test_last_week_may_be_light(budget: Budget) -> None:
    light_last = plan([full_week("Plein", [120] * 5), full_week("Léger", [30])])
    assert check_draft(light_last, budget) == []
    assert check_draft(plan([full_week("Seule", [30])]), budget) == []


def test_week_at_the_floor_is_not_underloaded(budget: Budget) -> None:
    at_floor = full_week("Juste", [120, 120, 108, 15])  # 363 + 65 = 428
    assert check_draft(plan([at_floor, full_week("Fin", [30])]), budget) == []


def test_schedule_pulls_tasks_forward_into_light_week() -> None:
    plan_ = schedule(_two_weeks_first_known(), Budget(120, 240), {"python": "declare"}, MONDAY)
    first, second = plan_.weeks
    assert first.load_minutes >= 428 and all(w.load_minutes <= 714 for w in plan_.weeks)
    assert second.tasks[-1].type == "quiz"  # quiz et pratique de la semaine 2 restés
    assert "pratiquer" in {t.type for t in second.tasks}
    assert (
        first.tasks[-1].type == "quiz" and first.tasks[-1].title == "Faire le quiz de la semaine 1"
    )
    moved = [t for t in first.tasks if t.title.startswith("Lire le chapitre")]
    assert [t.title for t in moved] == [
        "Lire le chapitre 1",
        "Lire le chapitre 2",
        "Lire le chapitre 3",
    ]
    assert {first.modules[t.module_index].title for t in moved} == {"Module Projet (suite)"}
    assert all(first.start_date <= t.planned_date <= first.tasks[-1].planned_date for t in moved)
    assert second.modules[0].title == "Module Projet"
    assert first.load_minutes == sum(t.minutes for t in first.tasks)
    assert second.load_minutes == sum(t.minutes for t in second.tasks)

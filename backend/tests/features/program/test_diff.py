from datetime import date

from app.features.program.service.budget import Budget
from app.features.program.service.diff import (
    ModuleRow,
    PlanDiff,
    ProgramRows,
    TaskRow,
    WeekRow,
    diff_plans,
    snapshot,
)
from app.features.program.service.planning import schedule
from tests.support.program import MONDAY, full_week, module, plan, task, week


def _snap(titles_by_day: dict[str, date]) -> dict[str, object]:
    tasks = [
        {
            "title": t,
            "type": "lire",
            "minutes": 30,
            "planned_date": d.isoformat(),
            "already_known": False,
        }
        for t, d in titles_by_day.items()
    ]
    return {"weeks": [{"rank": 1, "modules": [{"title": "Python", "tasks": tasks}]}], "skipped": []}


def test_diff_plans_lists_added_removed_moved() -> None:
    before = _snap({"Lire un": date(2026, 11, 16), "Lire deux": date(2026, 11, 17)})
    after = _snap({"Lire un": date(2026, 11, 18), "Lire trois": date(2026, 11, 19)})
    diff = diff_plans(before, after)
    assert diff == PlanDiff(
        added=["Python / Lire trois"],
        removed=["Python / Lire deux"],
        moved=[("Python / Lire un", "2026-11-16", "2026-11-18")],
        weeks_before=1,
        weeks_after=1,
    )


def test_first_version_adds_everything() -> None:
    after = _snap({"Lire un": date(2026, 11, 16), "Lire deux": date(2026, 11, 17)})
    diff = diff_plans(None, after)
    assert diff.added == ["Python / Lire un", "Python / Lire deux"]
    assert (diff.removed, diff.moved, diff.weeks_before, diff.weeks_after) == ([], [], 0, 1)


def test_identical_plans_have_an_empty_diff() -> None:
    snap = _snap({"Lire un": date(2026, 11, 16)})
    diff = diff_plans(snap, snap)
    assert (diff.added, diff.removed, diff.moved) == ([], [], [])


def test_duplicate_titles_in_a_module_are_kept_apart() -> None:
    snap = _snap({"Lire un": date(2026, 11, 16)})
    module_tasks = snap["weeks"][0]["modules"][0]["tasks"]  # type: ignore[index]
    module_tasks.append(dict(module_tasks[0], planned_date="2026-11-17"))
    diff = diff_plans(None, snap)
    assert diff.added == ["Python / Lire un", "Python / Lire un (2)"]


def test_snapshot_of_a_scheduled_plan_is_json_and_diffable() -> None:
    budget = Budget(120, 240)
    result = schedule(plan([full_week("Gros", [120] * 8)]), budget, {}, MONDAY)
    snap = snapshot(result)
    assert snap["skipped"] == [] and len(snap["weeks"]) == 2
    first = snap["weeks"][0]
    assert first["start_date"] == "2026-11-16" and first["modules"][0]["title"] == "Module Gros"
    assert isinstance(first["modules"][0]["tasks"][0]["planned_date"], str)
    assert diff_plans(snap, snap).moved == []
    assert diff_plans(None, snap).weeks_after == 2


def test_replanning_reports_moved_tasks() -> None:
    draft = plan([week("Bases", [module("Intro", [task("Lire un", minutes=60)])])])
    first = snapshot(schedule(draft, Budget(120, 240), {}, MONDAY))
    later = snapshot(schedule(draft, Budget(120, 240), {}, date(2026, 11, 23)))
    diff = diff_plans(first, later)
    assert diff.added == [] and diff.removed == []
    assert {m[0] for m in diff.moved} >= {"Intro / Lire un"}


def test_snapshot_from_program_rows_matches_the_plan_form() -> None:
    rows = ProgramRows(
        weeks=[
            WeekRow(
                rank=1,
                theme="Bases",
                start_date=date(2026, 11, 16),
                modules=[
                    ModuleRow("Python", skipped=True),
                    ModuleRow(
                        "Pandas",
                        tasks=[TaskRow("Réviser : Pandas", "lire", 20, date(2026, 11, 16), True)],
                    ),
                ],
            )
        ]
    )
    snap = snapshot(rows)
    assert snap["skipped"] == ["Python"]
    assert [m["title"] for m in snap["weeks"][0]["modules"]] == ["Pandas"]
    task_json = snap["weeks"][0]["modules"][0]["tasks"][0]
    assert task_json == {
        "title": "Réviser : Pandas",
        "type": "lire",
        "minutes": 20,
        "planned_date": "2026-11-16",
        "already_known": True,
    }


def test_plan_diff_to_json() -> None:
    diff = PlanDiff(["a"], ["b"], [("c", "2026-11-16", "2026-11-17")], 1, 2)
    assert diff.to_json() == {
        "added": ["a"],
        "removed": ["b"],
        "moved": [["c", "2026-11-16", "2026-11-17"]],
        "weeks_before": 1,
        "weeks_after": 2,
    }

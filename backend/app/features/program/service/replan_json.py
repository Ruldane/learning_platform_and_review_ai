"""Ce qu'une version de replanification garde en JSON (D106) : charges des semaines touchées
(`week_loads`), ce qu'il faut écrire à l'acceptation (`snapshot.changes`) et le résumé rendu au
Stratège (`PreviewSaved`). Fonctions pures, sans base."""

from datetime import date
from typing import Any

from app.agents.tools.replan_port import PreviewSaved, WeekLoad
from app.db.models.program import PlanVersion
from app.features.program.service.replan_rows import NewWeek, PlannedTask
from app.features.program.service.replanning import RepackResult


def loads_json(result: RepackResult | None, kept: int) -> dict[str, Any]:
    loads = result.loads if result is not None else []
    return {
        "loads": [
            {
                "rank": w.rank,
                "start_date": w.start_date.isoformat(),
                "before": w.before,
                "after": w.after,
                "cap": w.cap,
            }
            for w in loads
        ],
        "kept": kept,
    }


def loads_of(version: PlanVersion) -> list[WeekLoad]:
    raw = (version.week_loads or {}).get("loads", [])
    return [
        WeekLoad(
            int(w["rank"]),
            date.fromisoformat(str(w["start_date"])),
            int(w["before"]),
            int(w["after"]),
            int(w["cap"]),
        )
        for w in raw
    ]


def changes_json(result: RepackResult | None, *, finished: bool = False) -> dict[str, Any]:
    """Ce qu'il faut écrire à l'acceptation ; `finished` : impossible car le programme est
    terminé (le texte de fin le dit, D106)."""
    if result is None:
        return {"tasks": [], "removed": [], "new_weeks": [], "finished": finished}
    return {
        "tasks": [t.to_json() for t in result.tasks],
        "removed": list(result.removed),
        "new_weeks": [w.to_json() for w in result.new_weeks],
    }


def saved_of(version: PlanVersion) -> PreviewSaved:
    diff: dict[str, Any] = version.diff or {}
    added, removed = list(diff.get("added", [])), list(diff.get("removed", []))
    moved = list(diff.get("moved", []))
    weeks_before, weeks_after = int(diff.get("weeks_before", 0)), int(diff.get("weeks_after", 0))
    return PreviewSaved(
        version=version.version,
        empty=not (added or removed or moved) and weeks_before == weeks_after,
        added=len(added),
        removed=len(removed),
        moved=len(moved),
        weeks_before=weeks_before,
        weeks_after=weeks_after,
        loads=loads_of(version),
        kept=int((version.week_loads or {}).get("kept", 0)),
        impossible=version.status == "impossible",
        finished=bool((version.snapshot or {}).get("changes", {}).get("finished", False)),
    )


def earliest_date(changes: dict[str, Any]) -> date | None:
    """Le premier jour qu'écrirait l'acceptation (tâches datées, semaines « Suite »)."""
    days = [PlannedTask.from_json(t).planned_date for t in changes.get("tasks", [])]
    days += [NewWeek.from_json(w).start_date for w in changes.get("new_weeks", [])]
    return min(days, default=None)

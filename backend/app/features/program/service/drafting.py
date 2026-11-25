"""Writing a Strategist version (port `ProgramStore.save_draft`, D86, D88): the draft is packed by
the rules of 4.2 (`schedule`: learned items, 85%, practice and quiz), its rows replace those of
the program (weeks, modules, tasks) and a `plan_versions` row keeps the snapshot and the
difference with the replaced plan (January's edits included).

Idempotent by `(session, revision)`: a revision already written is returned as is."""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.council_port import GoalBrief
from app.agents.tools.plan_schema import KnownSkills, PlanDraft
from app.agents.tools.program_port import DraftSaved
from app.core.errors import AppError
from app.db.models.program import PlanVersion, Program
from app.db.models.skills import SkillLevel
from app.features.memory.service.skill_levels import acquis_levels
from app.features.program.repository import (
    ModuleRepository,
    PlanVersionRepository,
    ProgramRepository,
    TaskRepository,
    WeekRepository,
)
from app.features.program.service.budget import Budget, budget_for
from app.features.program.service.diff import diff_plans, snapshot
from app.features.program.service.planning import ScheduledPlan, next_monday, schedule
from app.features.program.service.programs import load, program_not_found, rows_of
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillsService, higher_level


def nothing_to_plan() -> AppError:
    return AppError("nothing_to_plan", "You already know everything covered by this program.", 422)


async def budget_of(db: AsyncSession, user_id: str, goal_weekly_minutes: int | None) -> Budget:
    settings = await SettingsService(db, user_id).get()
    return budget_for(settings.availability, goal_weekly_minutes)


async def known_skills(db: AsyncSession, user_id: str) -> dict[str, SkillLevel]:
    """The highest level between `user_skills` and the memory's learned items (those of the
    Archivist have no `user_skills` row), by normalized name."""
    known: dict[str, SkillLevel] = dict(await SkillsService(db, user_id).known_levels())
    for name, level in (await acquis_levels(db, user_id)).items():
        known[name] = higher_level(known[name], level) if name in known else level
    return known


def saved_of(version: PlanVersion) -> DraftSaved:
    snap: dict[str, Any] = version.snapshot
    tasks = [t for w in snap.get("weeks", []) for m in w["modules"] for t in m["tasks"]]
    return DraftSaved(
        program_id=version.program_id,
        version=version.version,
        weeks=len(snap.get("weeks", [])),
        total_minutes=sum(int(t["minutes"]) for t in tasks),
        skipped_modules=[str(title) for title in snap.get("skipped", [])],
        moved_tasks=int(snap.get("moved_tasks", 0)),
    )


async def write_rows(
    db: AsyncSession, user_id: str, program_id: str, plan: ScheduledPlan, draft: PlanDraft
) -> dict[str, int]:
    """Weeks, modules and tasks of the packed plan; skipped modules (already learned) are kept in
    the first week, marked `skipped`, without a task."""
    weeks, modules = WeekRepository(db, user_id), ModuleRepository(db, user_id)
    tasks = TaskRepository(db, user_id)
    first_week_id = ""
    chapter_indices: dict[str, int] = {}
    for week in plan.weeks:
        row = await weeks.add(
            program_id=program_id,
            rank=week.rank,
            theme=week.theme,
            objective=week.objective,
            deliverable=week.deliverable,
            start_date=week.start_date,
            stage=week.stage,
            rationale=week.rationale,
        )
        first_week_id = first_week_id or row.id
        ids: list[str] = []
        for rank, module in enumerate(week.modules):
            fields: dict[str, Any] = {"title": module.title, "skills": list(module.skills)}
            fields["prerequisites"] = list(module.prerequisites)
            fields["official_urls"] = list(module.official_urls)
            fields["legacy"] = list(module.legacy)
            added = await modules.add(week_id=row.id, program_id=program_id, rank=rank, **fields)
            ids.append(added.id)
            if module.chapter_index is not None:
                chapter_indices[added.id] = module.chapter_index
        for rank, task in enumerate(week.tasks):
            await tasks.add(
                module_id=ids[task.module_index],
                program_id=program_id,
                rank=rank,
                title=task.title,
                type=task.type,
                minutes=task.minutes,
                done_criterion=task.done_criterion,
                planned_date=task.planned_date,
                already_known=task.already_known,
            )
    await _write_skipped(modules, first_week_id, program_id, plan, draft)
    return chapter_indices


async def _write_skipped(
    modules: ModuleRepository,
    first_week_id: str,
    program_id: str,
    plan: ScheduledPlan,
    draft: PlanDraft,
) -> None:
    sources = {m.title: m for w in draft.weeks for m in w.modules}
    count = len(plan.weeks[0].modules) if plan.weeks else 0
    for offset, title in enumerate(plan.skipped_modules):
        source = sources.get(title)
        await modules.add(
            week_id=first_week_id,
            program_id=program_id,
            rank=count + offset,
            title=title,
            skills=list(source.skills) if source else [],
            prerequisites=list(source.prerequisites) if source else [],
            official_urls=list(source.official_urls) if source else [],
            legacy=list(source.legacy) if source else [],
            skipped=True,
        )


def plan_snapshot(
    plan: ScheduledPlan, draft: PlanDraft, budget: Budget, chapter_indices: dict[str, int]
) -> dict[str, Any]:
    """Snapshot of D83, plus the budget per day, the carry-overs and the Strategist's reference data
    (re-read at validation for the skill graph)."""
    return {
        **snapshot(plan),
        "chapters": [
            chapter.model_dump(mode="json", include={"title", "requires", "introduces"})
            for week in draft.weeks
            for chapter in week.modules
        ],
        "chapter_indices": chapter_indices,
        "budget": {
            "weekday_minutes": budget.weekday_minutes,
            "weekend_minutes": budget.weekend_minutes,
        },
        "moved_tasks": plan.moved_tasks,
        "catalog": {
            "skills": [s.model_dump(mode="json") for s in draft.skills],
            "edges": [e.model_dump(mode="json") for e in draft.edges],
        },
    }


async def _program_row(
    db: AsyncSession, user_id: str, goal_id: str, session_id: str, start: date, title: str
) -> tuple[Program, dict[str, Any] | None]:
    """The program of the session (and the snapshot of its current rows), otherwise a new one."""
    programs = ProgramRepository(db, user_id)
    program = await programs.by_session(session_id)
    if program is None:
        created = await programs.add(
            goal_id=goal_id,
            title=title,
            version=0,
            status="draft",
            start_date=start,
            weekly_minutes=0,
            cap_minutes=0,
            session_id=session_id,
        )
        return created, None
    if program.goal_id != goal_id:
        raise program_not_found()
    before = snapshot(rows_of(await load(db, user_id, program.id)))
    await WeekRepository(db, user_id).delete_for_program(program.id)
    return program, before


async def save_version(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    goal: GoalBrief,
    draft: PlanDraft,
    *,
    revision: int,
    start_date: date | None,
    reason: str,
    today: date,
) -> DraftSaved:
    """Packs the draft and saves it (program, rows, version); the commit belongs to the caller. A
    revision keeps the program's start date (January may have changed it)."""
    versions = PlanVersionRepository(db, user_id)
    existing = await versions.by_revision(session_id, revision)
    if existing is not None:
        return saved_of(existing)
    budget = await budget_of(db, user_id, goal.weekly_minutes)
    known: KnownSkills = await known_skills(db, user_id)
    current = await ProgramRepository(db, user_id).by_session(session_id)
    start = current.start_date if current else (start_date or next_monday(today))
    plan = schedule(draft, budget, known, start)
    if not plan.weeks:
        raise nothing_to_plan()
    program, before = await _program_row(db, user_id, goal.goal_id, session_id, start, draft.title)
    chapter_indices = await write_rows(db, user_id, program.id, plan, draft)
    after = plan_snapshot(plan, draft, budget, chapter_indices)
    number = await versions.next_version(program.id)
    await versions.supersede_pending(program.id)  # the new proposal replaces the old one
    version = await versions.add(
        program_id=program.id,
        version=number,
        snapshot=after,
        diff=diff_plans(before, after).to_json(),
        reason=reason[:300],
        session_id=session_id,
        revision=revision,
    )
    program.title, program.version, program.start_date = draft.title, number, start
    program.weekly_minutes, program.cap_minutes = budget.weekly_minutes, budget.cap_minutes
    await db.flush()
    return saved_of(version)

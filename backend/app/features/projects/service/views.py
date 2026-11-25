"""Reading projects (14.2, D166): the project as the API returns it (brief, submissions from the
last to the first, assessment with the text of each criterion, four drafts in a fixed order) and
the Portfolio row (program, week, rank). Statuses are corrected before any read (`settle`): the
status follows the session. JSON columns are read defensively: a damaged row is returned
without that part, never as an error."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.project_schema import DRAFT_KINDS
from app.core.errors import AppError
from app.db.models.daily import Project
from app.features.program.service.programs import Loaded, load
from app.features.projects.repository import ProjectRepository
from app.features.projects.schemas import (
    CriterionOut,
    DraftOut,
    EvaluationOut,
    ProfileEntryIn,
    ProjectBriefOut,
    ProjectOut,
    ProjectStatus,
    ProjectSummary,
    SubmissionOut,
)
from app.features.projects.service.errors import project_not_found
from app.features.projects.service.runtime import REVIEW_GRAPH, SUBJECT, ProjectsRuntime
from app.features.projects.service.settle import settle_all
from app.features.sessions.service import list_open_sessions_by_subject

_LIVE = ("brief_pending", "reviewing")  # statuses that have a session to follow
OpenSessions = Mapping[str, Sequence[str]]  # `project_review` sessions open, per project


def _session_id(row: Project, open_sessions: OpenSessions | None) -> str | None:
    """The session to follow: that of a brief or an assessment in progress; for a validated project,
    that of its drafts while it is open (the status does not move: without it, reloading the page
    would not find it)."""
    if row.status in _LIVE:
        return row.session_id
    if row.status == "validated" and row.session_id and open_sessions:
        return row.session_id if row.session_id in open_sessions.get(row.id, ()) else None
    return None


def parse_moment(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def brief_out(row: Project) -> ProjectBriefOut | None:
    return ProjectBriefOut.model_validate(row.brief) if row.brief else None


def submissions_out(row: Project) -> list[SubmissionOut]:
    """The submissions, the last one first."""
    out: list[SubmissionOut] = []
    for item in reversed(row.submissions):
        at = parse_moment(item.get("at"))
        if at is None:
            continue
        out.append(
            SubmissionOut(
                at=at,
                repo_url=item.get("repo_url"),
                description=item.get("description"),
                screenshots=len(item.get("screenshots", [])),
            )
        )
    return out


def evaluation_out(row: Project) -> EvaluationOut | None:
    data: dict[str, Any] | None = row.evaluation
    if not data:
        return None
    criteria: list[str] = list((row.brief or {}).get("criteria", []))
    results = [
        CriterionOut(
            index=int(item["index"]),
            criterion=criteria[int(item["index"]) - 1]
            if 0 < int(item["index"]) <= len(criteria)
            else "",
            met=bool(item["met"]),
            comment=str(item.get("comment", "")),
        )
        for item in data.get("results", [])
    ]
    return EvaluationOut(
        at=parse_moment(data.get("at")),
        verdict=data["verdict"],
        results=results,
        feedback=str(data.get("feedback", "")),
        repo_status=data.get("repo_status", "none"),
    )


def drafts_out(row: Project) -> list[DraftOut]:
    """The drafts in the fixed order of types; a missing type is not returned."""
    out: list[DraftOut] = []
    for kind in DRAFT_KINDS:
        item = row.drafts.get(kind)
        if not item:
            continue
        entry = item.get("entry")
        out.append(
            DraftOut(
                kind=kind,
                status=item["status"],
                content=str(item.get("content", "")),
                entry=ProfileEntryIn.model_validate(entry) if entry else None,
                flags=[str(flag) for flag in item.get("flags", [])],
                edited=bool(item.get("edited", False)),
            )
        )
    return out


def project_out(row: Project, open_sessions: OpenSessions | None = None) -> ProjectOut:
    return ProjectOut(
        id=row.id,
        module_id=row.module_id,
        program_id=row.program_id,
        title=row.title,
        status=_status(row),
        brief=brief_out(row),
        submissions=submissions_out(row),
        evaluation=evaluation_out(row),
        drafts=drafts_out(row),
        validated_at=row.validated_at,
        profile_version=row.profile_version,
        session_id=_session_id(row, open_sessions),
    )


def _status(row: Project) -> ProjectStatus:
    status: ProjectStatus = row.status  # type: ignore[assignment]  # colonne texte, `ProjectStatus`
    return status


async def get_project(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, project_id: str
) -> ProjectOut:
    """The user's project, its corrected status; 404 `project_not_found` otherwise."""
    await settle_all(rt, user_id)
    row = await ProjectRepository(db, user_id).get_fresh(project_id)
    if row is None:
        raise project_not_found()
    return await project_out_live(db, user_id, row)


async def project_out_live(db: AsyncSession, user_id: str, row: Project) -> ProjectOut:
    """The project as `GET /projects/{id}` returns it, `session_id` included: a validated project
    whose drafts session is running returns it. For the routes that return the project after an
    edit."""
    open_sessions = await list_open_sessions_by_subject(
        db, user_id, graph=REVIEW_GRAPH, subject_type=SUBJECT
    )
    return project_out(row, open_sessions)


async def _loaded(db: AsyncSession, user_id: str, program_id: str) -> Loaded | None:
    try:
        return await load(db, user_id, program_id)
    except AppError:  # program deleted: the project is returned without its place
        return None


def _summary(
    row: Project, loaded: Loaded | None, open_sessions: OpenSessions | None = None
) -> ProjectSummary:
    module = next((m for m in loaded.modules if m.id == row.module_id), None) if loaded else None
    week = (
        next((w for w in loaded.weeks if module and w.id == module.week_id), None)
        if loaded
        else None
    )
    hours = (row.brief or {}).get("hours")
    return ProjectSummary(
        id=row.id,
        module_id=row.module_id,
        program_id=row.program_id,
        program_title=loaded.program.title if loaded else None,
        title=row.title,
        status=_status(row),
        week=week.rank if week else None,
        rank=module.rank if module else None,
        hours=int(hours) if hours else None,
        skills=[str(skill) for skill in module.skills] if module else [],
        validated_at=row.validated_at,
        profile_version=row.profile_version,
        session_id=_session_id(row, open_sessions),
    )


async def list_projects(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, status: str | None
) -> list[ProjectSummary]:
    """The Portfolio: the projects (those of this status if given), in program order (the oldest
    first), by week then by module; without a place, at the end."""
    await settle_all(rt, user_id)
    rows = await ProjectRepository(db, user_id).all(status)
    programs: dict[str, Loaded | None] = {}
    for row in rows:
        if row.program_id not in programs:
            programs[row.program_id] = await _loaded(db, user_id, row.program_id)
    open_sessions = await list_open_sessions_by_subject(
        db, user_id, graph=REVIEW_GRAPH, subject_type=SUBJECT
    )
    summaries = [_summary(row, programs[row.program_id], open_sessions) for row in rows]
    order = {program_id: number for number, program_id in enumerate(programs)}
    big = 10**6
    summaries.sort(
        key=lambda s: (
            order[s.program_id],
            s.week if s.week is not None else big,
            s.rank if s.rank is not None else big,
        )
    )
    return summaries


@dataclass(frozen=True)
class RecentProject:
    id: str
    title: str
    verdict: str  # `validated` or `to_redo`
    ref: str  # the assessment's session: changes with each new assessment, never without
    at: datetime


async def recent_projects(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[RecentProject]:
    """The projects whose last assessment (validated or to redo) dates from `[after, before]`
    (bounds included), most recent first (activity feed, 8.10). A project that is submitted again
    (`reviewing`) is no longer in it until its new assessment. No submission data."""
    found: list[RecentProject] = []
    for row in await ProjectRepository(db, user_id).all():
        data: dict[str, Any] = row.evaluation or {}
        at = parse_moment(data.get("at")) or row.validated_at
        if (
            at is None
            or row.status not in ("validated", "to_redo")
            or data.get("verdict") != row.status
        ):
            continue
        if (after is not None and at < after) or (before is not None and at > before):
            continue
        ref = str(data.get("session_id") or data.get("at") or "")
        found.append(RecentProject(row.id, row.title, row.status, ref, at))
    found.sort(key=lambda item: (item.at, item.id), reverse=True)
    return found[:limit]

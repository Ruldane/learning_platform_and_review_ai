"""Lecture des projets (14.2, D166) : le projet rendu par l'API (énoncé, rendus du dernier au
premier, évaluation avec le texte de chaque critère, quatre brouillons dans un ordre fixe) et la
ligne du Portfolio (programme, semaine, rang). Les statuts sont corrigés avant toute lecture
(`settle`) : le statut suit la session. Les colonnes JSON sont lues défensivement : une ligne
abîmée se rend sans cette partie, jamais en erreur."""

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
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.settle import settle_all

_LIVE = ("brief_pending", "reviewing")  # statuts qui ont une session à suivre


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
    """Les rendus, le dernier d'abord."""
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
    """Les brouillons dans l'ordre fixe des types ; un type absent n'est pas rendu."""
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


def project_out(row: Project) -> ProjectOut:
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
        session_id=row.session_id if row.status in _LIVE else None,
    )


def _status(row: Project) -> ProjectStatus:
    status: ProjectStatus = row.status  # type: ignore[assignment]  # colonne texte, `ProjectStatus`
    return status


async def get_project(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, project_id: str
) -> ProjectOut:
    """Le projet de l'utilisatrice, son statut corrigé ; 404 `project_not_found` sinon."""
    await settle_all(rt, user_id)
    row = await ProjectRepository(db, user_id).get_fresh(project_id)
    if row is None:
        raise project_not_found()
    return project_out(row)


async def _loaded(db: AsyncSession, user_id: str, program_id: str) -> Loaded | None:
    try:
        return await load(db, user_id, program_id)
    except AppError:  # programme supprimé : le projet se rend sans sa place
        return None


def _summary(row: Project, loaded: Loaded | None) -> ProjectSummary:
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
        session_id=row.session_id if row.status in _LIVE else None,
    )


async def list_projects(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, status: str | None
) -> list[ProjectSummary]:
    """Le Portfolio : les projets (ceux de ce statut si donné), dans l'ordre des programmes (le
    plus ancien d'abord), des semaines puis des modules ; sans place, à la fin."""
    await settle_all(rt, user_id)
    rows = await ProjectRepository(db, user_id).all(status)
    programs: dict[str, Loaded | None] = {}
    for row in rows:
        if row.program_id not in programs:
            programs[row.program_id] = await _loaded(db, user_id, row.program_id)
    summaries = [_summary(row, programs[row.program_id]) for row in rows]
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
    verdict: str  # `validated` ou `to_redo`
    ref: str  # la session de l'évaluation : change avec chaque nouvelle évaluation, jamais sans
    at: datetime


async def recent_projects(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[RecentProject]:
    """Les projets dont la dernière évaluation (validée ou à reprendre) date de `[after, before]`
    (bornes incluses), la plus récente d'abord (fil d'activité, 8.10). Un projet qui se rend de
    nouveau (`reviewing`) n'y est plus jusqu'à sa nouvelle évaluation. Aucune donnée du rendu."""
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

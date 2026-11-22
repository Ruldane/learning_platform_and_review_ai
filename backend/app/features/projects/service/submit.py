"""Rendre un projet (P2, D166) : `POST /projects/{id}/submit`, sous le verrou du projet.

Le statut est d'abord corrigé (une session morte rend la main). Refus : énoncé absent (409
`project_not_ready`), évaluation en cours (409 `review_in_progress`, `details.session_id`), projet
déjà validé (409 `project_validated`). Puis le rendu : un lien http(s) et/ou une description
(`submission_problems`), cinq captures au plus de 5 Mo, vérifiées par leurs octets de tête ; une
422 nomme les champs (`repo_url`, `description`, `screenshots`), jamais leur valeur. Les captures
sont rangées, le rendu est ajouté aux `submissions` (dix au plus, les plus anciens et leurs
captures sont retirés), le projet passe en `reviewing` et la session `project_review` est lancée.
Un lancement refusé retire le rendu et ses captures, remet le statut d'avant et répond 503 lisible.
Journaux : identifiants et nombres, jamais le lien, la description ni un nom de fichier."""

import logging
from typing import Any
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.played import inherit_source
from app.db.models.daily import Project
from app.db.models.github_claims import ProjectGithubClaim
from app.features.projects.repository import ProjectRepository
from app.features.projects.schemas import SessionStarted
from app.features.projects.service.errors import (
    invalid_submission,
    project_not_found,
    project_not_ready,
    project_validated,
    review_in_progress,
    review_unavailable,
)
from app.features.projects.service.github import (
    get_github_claim,
    record_github_proof,
    verify_github_claim,
)
from app.features.projects.service.rules import SCREENSHOTS_MAX, submission_problems
from app.features.projects.service.runtime import (
    BRIEF_GRAPH,
    REVIEW_GRAPH,
    SUBJECT,
    ProjectsRuntime,
)
from app.features.projects.service.screenshots import (
    delete_all,
    detect_image,
    read_upload,
    store_all,
)
from app.features.projects.service.settle import settle_project
from app.features.sessions.service import find_latest_session, session_facts
from app.providers.github.base import RepoRef

logger = logging.getLogger(__name__)

MAX_SUBMISSIONS = 10


def _check_open(row: Project | None) -> Project:
    """Le projet s'il peut recevoir un rendu ; sinon l'erreur lisible."""
    if row is None:
        raise project_not_found()
    if row.status == "validated":
        raise project_validated()
    if row.status == "reviewing":
        raise review_in_progress(row.session_id)
    if row.status not in ("todo", "to_redo") or not row.brief:
        raise project_not_ready()
    return row


async def _images(files: list[UploadFile], problems: list[str]) -> list[tuple[bytes, str]]:
    """Les captures `(octets, type)` ; une image qui n'est ni PNG, ni JPEG, ni WebP ajoute
    `screenshots` aux problèmes. Aucune lecture au-delà de cinq fichiers."""
    if len(files) > SCREENSHOTS_MAX:
        return []
    found: list[tuple[bytes, str]] = []
    for file in files:
        data = await read_upload(file)
        media = detect_image(data)
        if media is None:
            if "screenshots" not in problems:
                problems.append("screenshots")
        else:
            found.append((data, media))
    return found


async def _append(
    rt: ProjectsRuntime, user_id: str, project_id: str, entry: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    """Ajoute le rendu et passe le projet en `reviewing` ; rend le statut d'avant et les rendus les
    plus anciens, écartés au-delà de dix (leurs captures ne sont retirées qu'une fois le lancement
    réussi)."""
    async with rt.session_factory() as db:
        row = await ProjectRepository(db, user_id).get_fresh(project_id)
        if row is None:
            raise project_not_found()
        previous = row.status
        dropped = _save_submission(row, entry, None)
        await db.commit()
    return previous, dropped


def _save_submission(
    row: Project, entry: dict[str, Any], session_id: str | None
) -> list[dict[str, Any]]:
    rows = [*row.submissions, entry]
    row.submissions, row.status, row.session_id = rows[-MAX_SUBMISSIONS:], "reviewing", session_id
    return rows[:-MAX_SUBMISSIONS]


async def _rollback(
    rt: ProjectsRuntime,
    user_id: str,
    project_id: str,
    entry: dict[str, Any],
    previous: str,
    dropped: list[dict[str, Any]],
) -> None:
    """Retire le rendu et ses captures, rend les rendus écartés, remet le statut d'avant
    (lancement refusé)."""
    async with rt.session_factory() as db:
        row = await ProjectRepository(db, user_id).get_fresh(project_id)
        if row is not None:
            rows = list(row.submissions)
            if rows and rows[-1] == entry:  # le rendu qu'on vient d'ajouter, le dernier
                rows.pop()
            row.submissions = [*dropped, *rows]
            row.status, row.session_id = previous, None
            await db.commit()
    await delete_all(rt, user_id, [str(key) for key in entry["screenshots"]])


async def _launch(
    rt: ProjectsRuntime,
    user_id: str,
    project_id: str,
    entry: dict[str, Any],
    previous: str,
    dropped: list[dict[str, Any]],
) -> str:
    """Lance `project_review` et pose la session sur le projet ; un lancement refusé retire le
    rendu (`_rollback`) et répond 503."""
    try:
        session_id = await rt.launcher.start(
            user_id,
            REVIEW_GRAPH,
            {"project_id": project_id},
            subject_type=SUBJECT,
            subject_id=project_id,
        )
    except Exception as exc:
        await _rollback(rt, user_id, project_id, entry, previous, dropped)
        logger.warning(
            "Évaluation non lancée : projet %s, cause %s", project_id, type(exc).__name__
        )
        raise review_unavailable() from None
    async with rt.session_factory() as db:
        row = await ProjectRepository(db, user_id).get_fresh(project_id)
        if row is not None:
            row.session_id = session_id
            await db.commit()
    return session_id


async def _launch_verified(
    rt: ProjectsRuntime,
    user_id: str,
    project_id: str,
    entry: dict[str, Any],
    claim: ProjectGithubClaim,
) -> tuple[str, list[dict[str, Any]]]:
    dropped: list[dict[str, Any]] = []

    async def prepare(db: AsyncSession, session_id: str) -> None:
        row = _check_open(await ProjectRepository(db, user_id).get_fresh(project_id))
        await record_github_proof(rt, db, row, claim, session_id)
        dropped.extend(_save_submission(row, entry, session_id))

    try:
        sid = await rt.launcher.start(
            user_id,
            REVIEW_GRAPH,
            {"project_id": project_id},
            subject_type=SUBJECT,
            subject_id=project_id,
            prepare=prepare,
        )
    except Exception as exc:
        await delete_all(rt, user_id, entry["screenshots"])
        if isinstance(exc, AppError) and exc.status_code < 500:
            raise
        logger.warning(
            "Évaluation GitHub non lancée : projet %s, cause %s", project_id, type(exc).__name__
        )
        raise review_unavailable() from None
    return sid, dropped


async def _entry(
    rt: ProjectsRuntime,
    user_id: str,
    repo_url: str | None,
    description: str | None,
    files: list[UploadFile],
) -> dict[str, Any]:
    link = (repo_url or "").strip() or None
    text = (description or "").strip() or None
    problems = submission_problems(link, text, len(files))
    images = await _images(files, problems)
    if problems:
        raise invalid_submission(problems)
    return {
        "at": rt.now().isoformat(),
        "repo_url": link,
        "description": text,
        "screenshots": await store_all(rt, user_id, images),
    }


async def submit_project(
    rt: ProjectsRuntime,
    user_id: str,
    project_id: str,
    *,
    repo_url: str | None,
    description: str | None,
    files: list[UploadFile],
    github_claim_id: UUID | None = None,
) -> SessionStarted:
    await settle_project(rt, user_id, project_id)
    async with rt.project_lock(user_id, project_id):
        claim = (
            await get_github_claim(rt, user_id, project_id, github_claim_id)
            if github_claim_id
            else None
        )
        if claim and claim.session_id:
            return SessionStarted(session_id=claim.session_id)
        async with rt.session_factory() as db:
            _check_open(await ProjectRepository(db, user_id).get_fresh(project_id))
            parent = await find_latest_session(
                db, user_id, graph=BRIEF_GRAPH, subject_type=SUBJECT, subject_id=project_id
            )
            source = await session_facts(db, user_id, parent) if parent else None
        if claim:
            await verify_github_claim(rt, claim)
            repo_url = RepoRef(claim.owner, claim.repository).url
        entry = await _entry(rt, user_id, repo_url, description, files)
        with inherit_source(
            user_id,
            source.played_by if source else None,
            source.model_provider if source else None,
            has_origin=source is not None,
        ):
            if claim:
                session_id, dropped = await _launch_verified(rt, user_id, project_id, entry, claim)
            else:
                previous, dropped = await _append(rt, user_id, project_id, entry)
                session_id = await _launch(rt, user_id, project_id, entry, previous, dropped)
    old_keys = [str(key) for item in dropped for key in item.get("screenshots", [])]
    await delete_all(rt, user_id, old_keys)
    logger.info(
        "Rendu reçu : projet %s, session %s, %d capture(s)",
        project_id,
        session_id,
        len(entry["screenshots"]),
    )
    return SessionStarted(session_id=session_id)

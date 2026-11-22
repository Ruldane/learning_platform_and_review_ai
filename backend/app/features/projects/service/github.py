"""Défi temporaire de contrôle du profil et preuve attachée au rendu."""

import asyncio
import re
from datetime import timedelta
from hashlib import sha256
from secrets import compare_digest, token_urlsafe
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.skills import evidence
from app.db.models.daily import Project
from app.db.models.github_claims import ProjectGithubClaim
from app.features.projects.github_repository import GithubClaimRepository
from app.features.projects.github_schemas import GithubClaimIn, GithubClaimOut, GithubProofOut
from app.features.projects.service.inputs import module_skills, owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.skills.service import SkillsService
from app.providers.github.base import GithubCommit, GithubContributions, RepoRef

_TTL = timedelta(minutes=15)
_CODE = re.compile(r"(?<![\w-])tremplin:[a-zA-Z0-9_-]{32}(?![\w-])")
_TIMEOUT = 20


def _digest(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def _repo(url: str) -> RepoRef:
    ref = RepoRef.from_url(url)
    if ref:
        parts = urlsplit(url)
        if (
            parts.scheme == "https"
            and parts.netloc.lower() in {"github.com", "www.github.com"}
            and len(parts.path.strip("/").split("/")) == 2
            and not (parts.query or parts.fragment)
        ):
            return ref
    raise AppError("github_invalid_repo", "Saisis l’adresse HTTPS d’un dépôt GitHub.", 422)


def _taken() -> AppError:
    return AppError("github_commit_claimed", "Ce commit figure déjà parmi tes preuves.", 409)


def _expired() -> AppError:
    return AppError("github_claim_expired", "Crée un nouveau code de vérification GitHub.", 409)


def _timeout() -> AppError:
    return AppError("github_unavailable", "GitHub n’a pas pu être lu. Réessaie plus tard.", 502)


async def _commit(port: GithubContributions, repo: RepoRef, sha: str) -> GithubCommit:
    try:
        async with asyncio.timeout(_TIMEOUT):
            return await port.attributed_commit(repo, sha)
    except TimeoutError:
        raise _timeout() from None


async def issue_github_claim(
    rt: ProjectsRuntime, user_id: str, project_id: str, body: GithubClaimIn
) -> GithubClaimOut:
    async with rt.session_factory() as db:
        project = await owned(db, user_id, project_id)
        if project.status not in ("todo", "to_redo") or not project.brief:
            raise AppError(
                "github_project_not_open", "Le projet ne peut pas recevoir de rendu.", 409
            )
    commit = await _commit(rt.github, _repo(body.repo_url), body.sha)
    code = f"tremplin:{token_urlsafe(24)}"
    until = rt.now() + _TTL
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        await owned(db, user_id, project_id)
        repo = GithubClaimRepository(db, user_id)
        if await repo.confirmed_sha(commit.sha):
            raise _taken()
        row = await repo.issue(
            project_id,
            repository_id=commit.repository_id,
            owner=commit.repo.owner,
            repository=commit.repo.repository,
            sha=commit.sha,
            author_id=commit.author_id,
            challenge_digest=_digest(code),
            expires_at=until,
        )
        await db.commit()
    return GithubClaimOut.model_validate(
        {
            "id": row.id,
            "profile_url": f"https://github.com/{commit.author_login}",
            "code": code,
            "expires_at": until,
        }
    )


async def get_github_claim(
    rt: ProjectsRuntime, user_id: str, project_id: str, claim_id: UUID
) -> ProjectGithubClaim:
    async with rt.session_factory() as db:
        await owned(db, user_id, project_id)
        claim = await GithubClaimRepository(db, user_id).get(project_id, str(claim_id))
    if claim is None:
        raise AppError("github_claim_not_found", "Défi GitHub introuvable.", 404)
    return claim


async def verify_github_claim(rt: ProjectsRuntime, claim: ProjectGithubClaim) -> None:
    digest = claim.challenge_digest
    if digest is None or claim.expires_at <= rt.now():
        raise _expired()
    try:
        async with asyncio.timeout(_TIMEOUT):
            ref = RepoRef(claim.owner, claim.repository)
            commit = await rt.github.attributed_commit(ref, claim.sha)
            if commit.repository_id != claim.repository_id or commit.author_id != claim.author_id:
                raise _expired()
            bio = await rt.github.public_bio(claim.author_id)
    except TimeoutError:
        raise _timeout() from None
    if not bio or not any(compare_digest(_digest(tag), digest) for tag in _CODE.findall(bio)):
        raise AppError(
            "github_code_missing", "Place le code fourni dans la bio GitHub de l’auteur.", 409
        )


async def record_github_proof(
    rt: ProjectsRuntime,
    db: AsyncSession,
    project: Project,
    claim: ProjectGithubClaim,
    session_id: str,
) -> None:
    repo = GithubClaimRepository(db, project.user_id)
    moment = rt.now()
    if await repo.confirmed_sha(claim.sha):
        raise _taken()
    if not await repo.consume(claim, session_id, moment):
        raise _expired()
    skills = await module_skills(db, project.user_id, project)
    if not skills:
        raise AppError("github_skills_missing", "Le projet n’a plus de compétences associées.", 409)
    proof = evidence(
        "github",
        f"{project.id}:{claim.id}",
        f"Contribution GitHub vérifiée ({claim.sha[:8]})",
        moment,
    )
    await SkillsService(db, project.user_id).raise_levels(skills, "en_cours", proof)


async def list_github_proofs(
    db: AsyncSession, user_id: str, project_id: str
) -> list[GithubProofOut]:
    await owned(db, user_id, project_id)
    rows = await GithubClaimRepository(db, user_id).confirmed(project_id)
    return [
        GithubProofOut.model_validate(
            {
                "commit_url": RepoRef(row.owner, row.repository).commit_url(row.sha),
                "sha": row.sha,
                "verified_at": row.verified_at,
            }
        )
        for row in rows
    ]

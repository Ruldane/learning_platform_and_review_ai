"""Sélection explicite de faits validés et de preuves publiques."""

from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import MasterProfileData
from app.features.cv.service.versions import validated_profile
from app.features.linkedin_drafts.service.actions import latest as read_linkedin
from app.features.portfolio.schemas import Candidate
from app.features.projects.service.github import list_github_proofs
from app.features.projects.service.validated_projects import validated_titles

MAX_PROJECTS = 20
MAX_PROOFS_PER_PROJECT = 4


def web_link(text: str | None) -> str | None:
    if not text or any(ch.isspace() or ch == "\\" for ch in text):
        return None
    try:
        url = urlsplit(text)
        _ = url.port
    except ValueError:
        return None
    if url.scheme != "https" or not url.hostname or url.username is not None:
        return None
    return text


def _profile_choices(profile: MasterProfileData) -> list[Candidate]:
    identity = profile.identity
    fields = [
        ("name", "Nom affiché", identity.name),
        (
            "headline",
            "Titre professionnel",
            profile.title.text if profile.title else identity.headline,
        ),
        ("summary", "Présentation", profile.summary.text if profile.summary else None),
    ]
    choices = [
        Candidate(id=key, kind="profile", label=label, text=text)
        for key, label, text in fields
        if text
    ]
    choices += [
        Candidate(id=f"skill:{item.id or index}", kind="skill", label=item.name, text=item.name)
        for index, item in enumerate(profile.skills)
    ]
    choices += [
        Candidate(
            id=f"profile-project:{item.id or index}",
            kind="project",
            label=item.name,
            text=item.description or item.name,
            url=web_link(item.link),
        )
        for index, item in enumerate(profile.projects)
    ]
    return choices


async def _linkedin(db: AsyncSession, user_id: str) -> list[Candidate]:
    draft = await read_linkedin(db, user_id)
    if draft is None or draft.state != "ready" or draft.text is None:
        return []
    blocked = {claim.field for claim in draft.claims}
    fields = [
        ("headline", "Titre LinkedIn relu", draft.text.headline),
        ("about", "Présentation LinkedIn relue", draft.text.about),
    ]
    return [
        Candidate(id=f"linkedin:{key}", kind="linkedin", label=label, text=text)
        for key, label, text in fields
        if key not in blocked
    ]


async def _projects(db: AsyncSession, user_id: str) -> list[Candidate]:
    out = []
    for project_id, title in await validated_titles(db, user_id, MAX_PROJECTS):
        out.append(Candidate(id=f"project:{project_id}", kind="project", label=title, text=title))
        proofs = await list_github_proofs(db, user_id, project_id)
        out.extend(
            Candidate(
                id=f"github:{project_id}:{proof.sha}",
                kind="github",
                label=title,
                text=f"Commit vérifié · {proof.sha[:12]}",
                url=web_link(str(proof.commit_url)),
            )
            for proof in proofs[:MAX_PROOFS_PER_PROJECT]
        )
    return out


async def choices(db: AsyncSession, user_id: str) -> list[Candidate]:
    profile = await validated_profile(db, user_id)
    chosen = _profile_choices(profile) if profile is not None else []
    if profile is not None:
        chosen.extend(await _linkedin(db, user_id))
    chosen.extend(await _projects(db, user_id))
    return chosen

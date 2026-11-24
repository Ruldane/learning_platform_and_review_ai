"""Editing a draft (rule 4, D166): `PATCH /projects/{id}/drafts/{kind}`, under the project's
lock. January's text replaces the draft's (`edited = true`): `content` for the CV line, the
LinkedIn post and the README outline; `entry` for the project entry (whose content becomes its
text, like `draft_text`). An edited `to_check` draft is checked again by `text_claims` against
**the same reference** as the Practitioner (validated profile, what January says about her
project, module skills, brief title allowed) and, for the LinkedIn post, the length of 80 to
200 words: `flags` is updated, the draft is `ready` if it is empty. An edited `ready` draft
stays `ready`: those are her words. Nothing enters the master profile here.
422 without echo (`fields`) if the field does not match the kind. Logs: identifiers only."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.project_schema import (
    LINKEDIN_WORDS,
    DraftKind,
    linkedin_words,
    project_fact,
    project_reference,
)
from app.agents.tools.text_claims import text_claims
from app.db.models.daily import Project
from app.features.cv.service.versions import validated_profile
from app.features.projects.schemas import DraftPatchIn, ProfileEntryIn, ProjectOut
from app.features.projects.service.errors import draft_not_found, invalid_submission
from app.features.projects.service.inputs import latest_submission, module_skills, owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import project_out_live

logger = logging.getLogger(__name__)


def entry_text(entry: ProfileEntryIn) -> str:
    """The project entry text that `text_claims` checks (like `draft_text`)."""
    return "\n".join([entry.name, entry.description, *entry.achievements]).strip()


def _new_content(kind: DraftKind, body: DraftPatchIn) -> tuple[str, ProfileEntryIn | None]:
    """The edited text and entry; 422 (`entry` or `content`) if the field does not fit the kind."""
    if kind == "profile_entry":
        if body.entry is None or body.content is not None:
            raise invalid_submission(["entry"])
        return entry_text(body.entry), body.entry
    text = (body.content or "").strip()
    if not text or body.entry is not None:
        raise invalid_submission(["content" if body.entry is None else "entry"])
    return text, None


async def _flags(
    db: AsyncSession, user_id: str, row: Project, kind: DraftKind, text: str
) -> list[str]:
    """The terms the reference does not state, then the LinkedIn post length if out of bounds."""
    submission = latest_submission(row)
    skills = await module_skills(db, user_id, row)
    title = str((row.brief or {}).get("title", row.title))
    fact = project_fact(title, submission.get("description"), skills, submission.get("repo_url"))
    reference = project_reference(await validated_profile(db, user_id), fact, skills)
    claims = text_claims(text, reference, allowed=[title])
    flags = list(dict.fromkeys(claim.term for claim in claims))
    low, high = LINKEDIN_WORDS
    words = linkedin_words(text)
    if kind == "linkedin_post" and not low <= words <= high:
        flags.append(f"{words} words ({low} to {high} expected)")
    return flags


async def patch_draft(
    rt: ProjectsRuntime, user_id: str, project_id: str, kind: DraftKind, body: DraftPatchIn
) -> ProjectOut:
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        item = (row.drafts or {}).get(kind)
        if not item:
            raise draft_not_found()
        text, entry = _new_content(kind, body)
        new = {
            **item,
            "content": text,
            "entry": entry.model_dump(mode="json") if entry else None,
            "edited": True,
        }
        if item.get("status") == "to_check":
            flags = await _flags(db, user_id, row, kind, text)
            new["flags"], new["status"] = flags, "to_check" if flags else "ready"
        row.drafts = {**row.drafts, kind: new}
        await db.commit()
        logger.info("Draft edited: project %s, kind %s, status %s", project_id, kind, new["status"])
        return await project_out_live(db, user_id, row)

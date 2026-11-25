from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.linkedin_port import GRAPH
from app.agents.tools.linkedin_profile import LinkedInText, check_text
from app.core.errors import AppError
from app.db.base import new_id
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.linkedin_drafts import LinkedInDraft
from app.features.cv.service.runtime import CvRuntime
from app.features.linkedin_drafts.repository import LinkedInRepository
from app.features.linkedin_drafts.schemas import (
    LinkedInDraftOut,
    LinkedInEdit,
    LinkedInStart,
    LinkedInState,
)
from app.features.linkedin_drafts.service.context import target_terms, verified_profile
from app.features.linkedin_drafts.service.store import owned, stale_profile
from app.features.sessions.service import session_facts


async def _active(db: AsyncSession, row: LinkedInDraft) -> bool:
    if row.revision:
        return False
    session = await session_facts(db, row.user_id, row.session_id)
    return session is not None and session.status in OPEN_SESSION_STATES


async def _view(db: AsyncSession, row: LinkedInDraft) -> LinkedInDraftOut:
    version, profile = await verified_profile(db, row.user_id)
    state: LinkedInState
    text = None
    if row.profile_version != version:
        state = "stale"
    elif row.text is None:
        state = "pending" if await _active(db, row) else "failed"
    else:
        state = "ready"
        text = LinkedInText.model_validate(row.text)
    return LinkedInDraftOut(
        id=row.id,
        revision=row.revision,
        session_id=row.session_id,
        profile_version=row.profile_version,
        state=state,
        text=text,
        claims=check_text(text, profile) if text is not None else [],
    )


async def latest(db: AsyncSession, user_id: str) -> LinkedInDraftOut | None:
    row = await LinkedInRepository(db, user_id).latest()
    return await _view(db, row) if row is not None else None


class _PendingDraft(Exception):
    def __init__(self, draft_id: str) -> None:
        self.draft_id = draft_id


async def start(rt: CvRuntime, user_id: str, body: LinkedInStart) -> LinkedInDraftOut:
    draft_id = new_id()

    async def prepare(db: AsyncSession, session_id: str) -> None:
        repo = LinkedInRepository(db, user_id)
        version, _ = await verified_profile(db, user_id)
        await target_terms(db, user_id, body.posting_id)
        current = await repo.latest()
        if current is not None and await _active(db, current):
            raise _PendingDraft(current.id)
        await repo.add(
            id=draft_id,
            session_id=session_id,
            profile_version=version,
            posting_id=body.posting_id,
        )

    try:
        await rt.launcher.start(
            user_id,
            GRAPH,
            {"draft_id": draft_id},
            subject_type=GRAPH,
            subject_id=draft_id,
            prepare=prepare,
        )
    except _PendingDraft as existing:
        draft_id = existing.draft_id
    async with rt.session_factory() as db:
        return await _view(db, await owned(db, user_id, draft_id))


async def edit(
    db: AsyncSession, user_id: str, draft_id: str, body: LinkedInEdit
) -> LinkedInDraftOut:
    row = await owned(db, user_id, draft_id)
    version, profile = await verified_profile(db, user_id)
    if row.profile_version != version:
        raise stale_profile()
    if not await LinkedInRepository(db, user_id).save(draft_id, body.text, revision=body.revision):
        raise AppError("linkedin_edit_conflict", "The proposal has changed. Reload it.", 409)
    await db.commit()
    return LinkedInDraftOut(
        id=draft_id,
        revision=body.revision + 1,
        session_id=row.session_id,
        profile_version=version,
        state="ready",
        text=body.text,
        claims=check_text(body.text, profile),
    )

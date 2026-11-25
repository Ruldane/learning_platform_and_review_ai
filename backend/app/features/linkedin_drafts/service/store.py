from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.cv_schema import facts_of
from app.agents.tools.linkedin_port import LinkedInContext
from app.agents.tools.linkedin_profile import LinkedInText
from app.core.errors import AppError
from app.db.models.linkedin_drafts import LinkedInDraft
from app.features.linkedin_drafts.repository import LinkedInRepository
from app.features.linkedin_drafts.service.context import target_terms, verified_profile


async def owned(db: AsyncSession, user_id: str, draft_id: str) -> LinkedInDraft:
    row = await LinkedInRepository(db, user_id).get(draft_id)
    if row is None:
        raise AppError("linkedin_draft_missing", "LinkedIn proposal not found.", 404)
    return row


def stale_profile() -> AppError:
    return AppError(
        "linkedin_profile_changed", "The profile has changed. Prepare a new proposal.", 409
    )


async def _assigned(
    db: AsyncSession, user_id: str, session_id: str, draft_id: str
) -> LinkedInDraft:
    row = await owned(db, user_id, draft_id)
    if row.session_id != session_id:
        raise AppError("linkedin_draft_missing", "LinkedIn proposal not found.", 404)
    return row


class AgentLinkedInStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, session_id: str, draft_id: str) -> LinkedInContext:
        async with self._factory() as db:
            row = await _assigned(db, user_id, session_id, draft_id)
            if row.revision:
                return LinkedInContext({}, (), (), True)
            version, profile = await verified_profile(db, user_id)
            if row.profile_version != version:
                raise stale_profile()
            terms = await target_terms(db, user_id, row.posting_id)
            return LinkedInContext(
                facts_of(profile), tuple(skill.name for skill in profile.skills), terms, False
            )

    async def propose(
        self, user_id: str, session_id: str, draft_id: str, text: LinkedInText
    ) -> None:
        async with self._factory() as db:
            row = await _assigned(db, user_id, session_id, draft_id)
            if row.revision == 0:
                await LinkedInRepository(db, user_id).save(row.id, text, revision=0)
                await db.commit()

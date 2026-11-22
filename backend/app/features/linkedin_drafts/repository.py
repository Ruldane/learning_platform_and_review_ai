from sqlalchemy import select, update

from app.agents.tools.linkedin_profile import LinkedInText
from app.db.models.linkedin_drafts import LinkedInDraft
from app.db.repository import UserScopedRepository


class LinkedInRepository(UserScopedRepository[LinkedInDraft]):
    model = LinkedInDraft

    async def latest(self) -> LinkedInDraft | None:
        stmt = (
            select(LinkedInDraft)
            .where(LinkedInDraft.user_id == self.user_id)
            .order_by(LinkedInDraft.created_at.desc(), LinkedInDraft.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def save(self, draft_id: str, text: LinkedInText, *, revision: int) -> bool:
        stmt = (
            update(LinkedInDraft)
            .where(
                LinkedInDraft.user_id == self.user_id,
                LinkedInDraft.id == draft_id,
                LinkedInDraft.revision == revision,
            )
            .values(text=text.model_dump(mode="json"), revision=revision + 1)
            .returning(LinkedInDraft.id)
        )
        return await self.session.scalar(stmt) is not None

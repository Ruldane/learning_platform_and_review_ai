from sqlalchemy import select

from app.db.models.project_handoffs import ProjectHandoff
from app.db.repository import UserScopedRepository


class ProjectHandoffs(UserScopedRepository[ProjectHandoff]):
    model = ProjectHandoff

    async def history(self) -> list[ProjectHandoff]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return list(await self.session.scalars(stmt))

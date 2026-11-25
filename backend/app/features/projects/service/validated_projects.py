from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.repository import ProjectRepository


async def validated_titles(db: AsyncSession, user_id: str, limit: int) -> list[tuple[str, str]]:
    """The latest validated projects usable in a write-up."""
    rows = await ProjectRepository(db, user_id).all("validated")
    return [(row.id, row.title) for row in rows[-limit:]]

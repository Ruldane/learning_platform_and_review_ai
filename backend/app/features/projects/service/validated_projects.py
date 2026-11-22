from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.repository import ProjectRepository


async def validated_titles(db: AsyncSession, user_id: str, limit: int) -> list[tuple[str, str]]:
    """Les derniers projets validés utilisables dans une rédaction."""
    rows = await ProjectRepository(db, user_id).all("validated")
    return [(row.id, row.title) for row in rows[-limit:]]

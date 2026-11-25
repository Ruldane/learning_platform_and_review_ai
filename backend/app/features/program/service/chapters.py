"""Table of contents of the Strategist's latest plan, in its teaching order."""

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.plan_schema import ChapterOutline
from app.features.program.repository import PlanVersionRepository, ProgramRepository


class ProgramOutline(BaseModel):
    chapters: list[ChapterOutline] = Field(default_factory=list)
    chapter_indices: dict[str, int] = Field(default_factory=dict)


async def program_outline(db: AsyncSession, user_id: str, program_id: str) -> ProgramOutline:
    version = await PlanVersionRepository(db, user_id).latest_with_catalog(program_id)
    if version is None:
        return ProgramOutline()
    return ProgramOutline.model_validate(version.snapshot)


async def validated_outlines(db: AsyncSession, user_id: str) -> list[ProgramOutline]:
    programs = await ProgramRepository(db, user_id).list_recent()
    return [
        await program_outline(db, user_id, row.id) for row in programs if row.status == "validated"
    ]

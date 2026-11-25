"""`existing_name`: a skill stored under its French name keeps receiving the proofs."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.plan_schema import SkillDraft
from app.features.skills.service import SkillsService

Factory = async_sessionmaker[AsyncSession]
USER = "moi"


async def test_existing_name_prefers_the_legacy_name_only_when_it_is_the_one_stored(
    db_session_factory: Factory,
) -> None:
    async with db_session_factory() as db:
        service = SkillsService(db, USER)
        assert await service.existing_name("Python development", "Développement Python") == (
            "Python development"
        )
        await service.upsert_catalog([SkillDraft(name="Développement Python", domain="Code")], [])
        await db.commit()
        assert await service.existing_name("Python development", "Développement Python") == (
            "Développement Python"
        )
        await service.upsert_catalog([SkillDraft(name="Python development", domain="Code")], [])
        await db.commit()
        assert await service.existing_name("Python development", "Développement Python") == (
            "Python development"
        )

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import MasterProfileData, Project
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.features.cv.service.versions import validated_profile_version
from app.features.postings.service.queries import get_posting
from app.features.projects.service.validated_projects import validated_titles


async def verified_profile(db: AsyncSession, user_id: str) -> tuple[int, MasterProfileData]:
    current = await validated_profile_version(db, user_id)
    if current is None:
        raise AppError(
            "profile_required", "Valide ton profil maître avant de préparer le texte.", 409
        )
    version, profile = current
    known = {row.name.casefold() for row in profile.projects}
    projects = [
        Project(id=f"projet-{key}", name=title[:120], description="Projet validé dans Tremplin.")
        for key, title in await validated_titles(db, user_id, 6)
        if title.strip() and title[:120].casefold() not in known
    ]
    data = profile.model_copy(update={"projects": [*profile.projects, *projects][:20], "links": []})
    return version, data


async def target_terms(db: AsyncSession, user_id: str, posting_id: str | None) -> tuple[str, ...]:
    if posting_id is None:
        return ()
    row = await get_posting(db, user_id, posting_id)
    if row.analysis is None:
        raise AppError("posting_not_ready", "Choisis une offre déjà analysée.", 409)
    analysis = PostingAnalysis.model_validate(row.analysis)
    return tuple(dict.fromkeys(item.name for item in analysis.skills))

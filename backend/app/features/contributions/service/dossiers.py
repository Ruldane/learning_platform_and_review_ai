"""Creates account-owned dossiers from an issue that is still suggested."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import new_id
from app.features.contributions.repository import ContributionRepository
from app.features.contributions.schemas import ContributionOut, CreateContribution, PublicationIn
from app.features.contributions.service.discovery import chapter_context
from app.features.contributions.service.matching import rank_issues
from app.features.contributions.service.runtime import ContributionRuntime
from app.features.contributions.service.views import view


async def list_dossiers(db: AsyncSession, user_id: str) -> list[ContributionOut]:
    return [view(row) for row in await ContributionRepository(db, user_id).list()]


async def get_dossier(db: AsyncSession, user_id: str, contribution_id: str) -> ContributionOut:
    return view(await ContributionRepository(db, user_id).owned(contribution_id))


def _issue_missing() -> AppError:
    return AppError("contribution_issue_missing", "This issue is no longer suggested.", 404)


async def create_dossier(
    runtime: ContributionRuntime, user_id: str, body: CreateContribution
) -> ContributionOut:
    repository_name = body.repository.lower()
    async with runtime.session_factory() as db:
        context = await chapter_context(db, user_id, body.program_id)
        existing = await ContributionRepository(db, user_id).by_issue(
            repository_name, body.issue_number
        )
        if existing is not None:
            return view(existing)
    if context is None:
        raise _issue_missing()
    repo = next((item for item in context.repositories if item.name == repository_name), None)
    if repo is None:
        raise _issue_missing()
    candidates = rank_issues(repo, await runtime.github.open_issues(repo), context.skills)
    suggestion = next((item for item in candidates if item.issue.number == body.issue_number), None)
    if suggestion is None:
        raise _issue_missing()
    branch = await runtime.github.default_branch(repo)
    async with runtime.session_factory() as db:
        row = await ContributionRepository(db, user_id).make(
            program_id=body.program_id,
            chapter_id=context.module_id,
            chapter_title=context.title,
            repository=repo.name,
            issue_number=suggestion.issue.number,
            issue_title=suggestion.issue.title,
            issue_body=suggestion.issue.body,
            skills=list(suggestion.skills),
            base=branch,
            marker=new_id(),
        )
        result = view(row)
        await db.commit()
    return result


async def approve_publication(
    db: AsyncSession, user_id: str, contribution_id: str, body: PublicationIn
) -> ContributionOut:
    repo = ContributionRepository(db, user_id)
    row = await repo.owned(contribution_id)
    payload = body.model_dump(mode="json")
    if row.publication == payload:
        return view(row)
    if row.status != "draft" or not await repo.change(row, publication=payload, status="confirmed"):
        raise AppError(
            "contribution_already_confirmed", "This preparation is already confirmed.", 409
        )
    return view(await repo.owned(contribution_id))

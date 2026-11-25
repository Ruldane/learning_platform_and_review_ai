"""Matches a public PR with the confirmed dossier and records the proof in the same transaction."""

from datetime import UTC, datetime

from app.core.errors import AppError
from app.core.skills import evidence
from app.features.contributions.repository import ContributionRepository
from app.features.contributions.schemas import ContributionOut, Status
from app.features.contributions.service.publication import markers_match
from app.features.contributions.service.runtime import ContributionRuntime
from app.features.contributions.service.views import publication_of, repository, view
from app.features.skills.service import SkillsService


def _unverified() -> AppError:
    return AppError(
        "contribution_pull_unverified",
        "The pull request does not match the confirmed account, branches and marker.",
        409,
    )


async def track(
    runtime: ContributionRuntime, user_id: str, contribution_id: str, url: str | None
) -> ContributionOut:
    async with runtime.session_factory() as db:
        row = await ContributionRepository(db, user_id).owned(contribution_id)
        approved = publication_of(row)
        if approved is None:
            raise AppError("contribution_not_confirmed", "Confirm the preparation first.", 409)
        repo = repository(row)
        number = row.pull_number if url is None else repo.pull_number(url)
        if number is None or (row.pull_number is not None and row.pull_number != number):
            raise _unverified()
        revision = row.revision
        if row.status == "accepted":
            return view(row)
    pull = await runtime.github.pull(repo, number)
    if pull.number != number or not markers_match(approved, pull):
        raise _unverified()
    status: Status = "accepted" if pull.merged else "closed" if pull.state == "closed" else "open"
    async with runtime.session_factory() as db:
        records = ContributionRepository(db, user_id)
        row = await records.owned(contribution_id)
        if row.revision != revision or not await records.change(
            row, pull_number=number, status=status
        ):
            raise AppError("contribution_changed", "This dossier has changed. Refresh it.", 409)
        if status == "accepted":
            proof = evidence(
                "contribution", contribution_id, row.issue_title[:200], datetime.now(UTC)
            )
            await SkillsService(db, user_id).raise_levels(
                [name for name in row.skills if isinstance(name, str)], "proven", proof
            )
        result = view(await records.owned(contribution_id))
        await db.commit()
    return result

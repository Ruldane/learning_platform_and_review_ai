from typing import cast

from app.db.models.contributions import Contribution
from app.features.contributions.schemas import (
    ContributionOut,
    PublicationIn,
    Status,
    SuggestedIssue,
)
from app.features.contributions.service.matching import Suggestion
from app.features.contributions.service.publication import Publication, compare_url
from app.providers.github.base import RepoRef


def repository(row: Contribution) -> RepoRef:
    owner, name = row.repository.split("/", 1)
    return RepoRef(owner, name)


def publication_of(row: Contribution) -> Publication | None:
    if row.publication is None:
        return None
    value = PublicationIn.model_validate(row.publication)
    return Publication(value.author, row.base, value.head, value.title, value.body, row.marker)


def suggested(item: Suggestion) -> SuggestedIssue:
    return SuggestedIssue(
        repository=item.repo.name,
        number=item.issue.number,
        title=item.issue.title,
        body=item.issue.body,
        url=item.repo.issue_url(item.issue.number),
        skills=list(item.skills),
    )


def view(row: Contribution) -> ContributionOut:
    repo = repository(row)
    publication = publication_of(row)
    pull_url = repo.pull_url(row.pull_number) if row.pull_number is not None else None
    cv_line = (
        f"{row.issue_title} — contribution acceptée à {repo.name} ({pull_url})"
        if row.status == "accepted"
        else None
    )
    return ContributionOut(
        id=row.id,
        program_id=row.program_id,
        chapter=row.chapter_title,
        status=cast(Status, row.status),
        base=row.base,
        issue=SuggestedIssue(
            repository=repo.name,
            number=row.issue_number,
            title=row.issue_title,
            body=row.issue_body,
            url=repo.issue_url(row.issue_number),
            skills=[skill for skill in row.skills if isinstance(skill, str)],
        ),
        publication_url=(
            compare_url(repo, row.issue_number, publication)
            if publication is not None and row.pull_number is None
            else None
        ),
        pull_url=pull_url,
        cv_line=cv_line,
    )

from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

from app.features.contributions.service.matching import rank_issues
from app.features.contributions.service.publication import (
    Publication,
    compare_url,
    markers_match,
)
from app.providers.github.base import GithubIssue, GithubPull, RepoRef

REPO = RepoRef("org-fictive", "bibliotheque")


def test_suggestions_keep_issues_for_the_current_skills() -> None:
    issues = [
        GithubIssue(
            9, "Réparer une requête SQL", "Améliorer la documentation", ("good first issue",)
        ),
        GithubIssue(7, "Retoucher le parseur Python", "Exemples", ("help wanted",)),
        GithubIssue(4, "Tests Python et SQL", "Scénarios unitaires", ("Good First Issue",)),
        GithubIssue(2, "Journal de publication", "Expliquer le calendrier", ("good first issue",)),
    ]

    ranked = rank_issues(REPO, issues, ("Python", "SQL"))

    assert [(item.issue.number, item.skills) for item in ranked] == [
        (4, ("Python", "SQL")),
        (9, ("SQL",)),
    ]


def test_compare_url_carries_only_the_confirmed_payload() -> None:
    publication = Publication("camille", "main", "docs/exemple", "Une correction", "Exemple", "m-1")
    link = urlsplit(compare_url(REPO, issue_number=4, publication=publication))
    assert (link.scheme, link.hostname) == ("https", "github.com")
    assert link.path == "/org-fictive/bibliotheque/compare/main...camille:docs%2Fexemple"
    assert parse_qs(link.query) == {
        "expand": ["1"],
        "title": ["Une correction"],
        "body": ["Exemple\n\nCloses #4\n\n<!-- tremplin-contribution:m-1 -->"],
    }


def test_pull_requires_the_published_marker_and_confirmed_author_and_branch() -> None:
    publication = Publication("camille", "main", "docs/exemple", "Une correction", "Exemple", "m-1")
    pull = GithubPull(
        12, "CAMilLe", "main", "docs/exemple", "<!-- tremplin-contribution:m-1 -->", True
    )
    assert markers_match(publication, pull)
    for foreign in (
        replace(pull, author="autre"),
        replace(pull, base="branche-etrangere"),
        replace(pull, head="branche-etrangere"),
        replace(pull, body="<!-- tremplin-contribution:m-10 -->"),
    ):
        assert not markers_match(publication, foreign)

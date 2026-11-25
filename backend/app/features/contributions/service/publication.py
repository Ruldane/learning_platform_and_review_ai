"""Content allowed before continuing the publication on GitHub."""

from dataclasses import dataclass
from urllib.parse import quote, urlencode

from app.providers.github.base import GithubPull, RepoRef


@dataclass(frozen=True)
class Publication:
    author: str
    base: str
    head: str
    title: str
    body: str
    marker: str


def _marker(value: str) -> str:
    return f"<!-- tremplin-contribution:{value} -->"


def compare_url(repo: RepoRef, issue_number: int, publication: Publication) -> str:
    base = quote(publication.base, safe="")
    head = quote(publication.head, safe="")
    author = quote(publication.author, safe="")
    body = f"{publication.body}\n\nCloses #{issue_number}\n\n{_marker(publication.marker)}"
    query = urlencode({"expand": "1", "title": publication.title, "body": body})
    return f"https://github.com/{repo.name}/compare/{base}...{author}:{head}?{query}"


def markers_match(publication: Publication, pull: GithubPull) -> bool:
    return (
        pull.author.casefold() == publication.author.casefold()
        and pull.base == publication.base
        and pull.head == publication.head
        and _marker(publication.marker) in pull.body
    )

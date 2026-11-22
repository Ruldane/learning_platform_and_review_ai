from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

from app.core.github_refs import github_repo


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repository: str

    @classmethod
    def from_url(cls, url: str) -> "RepoRef | None":
        repo = github_repo(url)
        return None if repo is None else cls(repo[0].lower(), repo[1].lower())

    @property
    def name(self) -> str:
        return f"{self.owner}/{self.repository}"

    def issue_url(self, number: int) -> str:
        return f"https://github.com/{self.name}/issues/{number}"

    def pull_url(self, number: int) -> str:
        return f"https://github.com/{self.name}/pull/{number}"

    def pull_number(self, url: str) -> int | None:
        try:
            parts = urlsplit(url)
        except ValueError:
            return None
        if parts.scheme != "https" or parts.netloc.lower() not in {"github.com", "www.github.com"}:
            return None
        segments = parts.path.strip("/").split("/")
        if len(segments) != 4 or "/".join(segments[:2]).lower() != self.name:
            return None
        number = segments[3]
        if segments[2] != "pull" or not number.isascii() or not number.isdecimal():
            return None
        if len(number) > 9 or int(number) < 1:
            return None
        return int(number)


@dataclass(frozen=True)
class GithubIssue:
    number: int
    title: str
    body: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class GithubPull:
    number: int
    author: str
    base: str
    head: str
    body: str
    merged: bool
    state: str = "open"


class GithubContributions(Protocol):
    async def open_issues(self, repo: RepoRef) -> tuple[GithubIssue, ...]: ...

    async def default_branch(self, repo: RepoRef) -> str: ...

    async def pull(self, repo: RepoRef, number: int) -> GithubPull: ...

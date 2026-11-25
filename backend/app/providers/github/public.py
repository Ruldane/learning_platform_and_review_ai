"""Lecture bornée de l'API publique, via le fetcher sûr déjà utilisé par la recherche."""

import json
import re
from typing import Any
from urllib.parse import quote

from app.core.errors import AppError
from app.providers.github.base import GithubCommit, GithubIssue, GithubPull, RepoRef
from app.providers.web.base import WebFetcher

API = "https://api.github.com/repos"
_HEADERS = {"Accept": "application/vnd.github+json"}
_LOGIN = re.compile(r"[a-zA-Z0-9-]{1,39}")
_SHA = re.compile(r"[a-f0-9]{40}")


def _unavailable() -> AppError:
    return AppError("github_unavailable", "GitHub could not be reached. Try again later.", 502)


def _identity(raw: object) -> int:
    return raw if type(raw) is int and 0 < raw < 2**63 else 0


def _commit_author(value: object, sha: str) -> tuple[int, str]:
    author = _field(value, "author")
    author_id = _identity(_field(author, "id"))
    login = _field(author, "login")
    committer_id = _identity(_field(_field(value, "committer"), "id"))
    signature = _field(_field(value, "commit"), "verification")
    if (
        _field(value, "sha") != sha
        or not author_id
        or author_id != committer_id
        or _field(author, "type") != "User"
        or not isinstance(login, str)
        or not _LOGIN.fullmatch(login)
        or _field(signature, "verified") is not True
        or _field(signature, "reason") != "valid"
    ):
        raise AppError(
            "github_commit_unverified",
            "Choose a signed commit that GitHub has verified and linked to its author.",
            409,
        )
    return author_id, login


def _str(raw: object, limit: int) -> str:
    return raw.strip()[:limit] if isinstance(raw, str) else ""


def _number(raw: object) -> int:
    return raw if type(raw) is int and 0 < raw < 10**9 else 0


def _labels(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        name for item in raw[:30] if isinstance(item, dict) and (name := _str(item.get("name"), 80))
    )


def _issue(raw: object) -> GithubIssue | None:
    if not isinstance(raw, dict) or raw.get("state") != "open" or "pull_request" in raw:
        return None
    number = _number(raw.get("number"))
    title = _str(raw.get("title"), 200)
    if not number or not title:
        return None
    return GithubIssue(number, title, _str(raw.get("body"), 3500), _labels(raw.get("labels")))


def _field(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None


def _pull(payload: dict[str, Any], number: int) -> GithubPull:
    author = _str(_field(payload.get("user"), "login"), 39)
    base = _str(_field(payload.get("base"), "ref"), 100)
    head = _str(_field(payload.get("head"), "ref"), 100)
    if _number(payload.get("number")) != number or not all((author, base, head)):
        raise _unavailable()
    return GithubPull(
        number,
        author,
        base,
        head,
        _str(payload.get("body"), 65_536),
        payload.get("merged") is True,
        _str(payload.get("state"), 10),
    )


class PublicGithub:
    def __init__(self, fetcher: WebFetcher) -> None:
        self._fetcher = fetcher

    async def _read(self, path: str) -> object:
        return await self._read_url(f"{API}/{path}")

    async def _read_url(self, url: str) -> object:
        try:
            result = await self._fetcher.fetch(
                url, content_types=("application/json",), headers=_HEADERS
            )
            value: object = json.loads(result.body)
        except (AppError, ValueError, RecursionError):
            raise _unavailable() from None
        return value

    async def open_issues(self, repo: RepoRef) -> tuple[GithubIssue, ...]:
        value = await self._read(f"{repo.name}/issues?state=open&per_page=50")
        if not isinstance(value, list):
            raise _unavailable()
        return tuple(issue for row in value[:50] if (issue := _issue(row)) is not None)

    async def default_branch(self, repo: RepoRef) -> str:
        branch = _str(_field(await self._read(repo.name), "default_branch"), 100)
        if not branch:
            raise _unavailable()
        return branch

    async def pull(self, repo: RepoRef, number: int) -> GithubPull:
        value = await self._read(f"{repo.name}/pulls/{number}")
        if not isinstance(value, dict):
            raise _unavailable()
        return _pull(value, number)

    async def attributed_commit(self, repo: RepoRef, sha: str) -> GithubCommit:
        if not _SHA.fullmatch(sha):
            raise AppError("github_invalid_sha", "Enter the full commit SHA.", 422)
        metadata = await self._read(repo.name)
        if _field(metadata, "private") is not False:
            raise AppError("github_repo_not_public", "Choose a public GitHub repository.", 409)
        repo_id = _identity(_field(metadata, "id"))
        branch = _field(metadata, "default_branch")
        full_name = _field(metadata, "full_name")
        if (
            not isinstance(full_name, str)
            or not isinstance(branch, str)
            or not 0 < len(branch) <= 255
        ):
            raise _unavailable()
        found = RepoRef.from_url(f"https://github.com/{full_name}")
        if not repo_id or found is None or found.name != full_name.lower():
            raise _unavailable()
        author_id, login = _commit_author(await self._read(f"{found.name}/commits/{sha}"), sha)
        comparison = await self._read(
            f"{found.name}/compare/{sha}...{quote(branch, safe='')}?per_page=1"
        )
        if (
            _field(comparison, "status") not in ("identical", "ahead")
            or _field(_field(comparison, "merge_base_commit"), "sha") != sha
        ):
            raise AppError(
                "github_commit_outside_branch",
                "Choose a commit from the default branch’s history.",
                409,
            )
        return GithubCommit(found, repo_id, sha, author_id, login)

    async def public_bio(self, author_id: int) -> str | None:
        profile = await self._read_url(f"https://api.github.com/user/{author_id:d}")
        if _identity(_field(profile, "id")) != author_id or _field(profile, "type") != "User":
            return None
        return _str(_field(profile, "bio"), 500)

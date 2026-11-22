"""Lecture bornée de l'API publique, via le fetcher sûr déjà utilisé par la recherche."""

import json
from typing import Any

from app.core.errors import AppError
from app.providers.github.base import GithubIssue, GithubPull, RepoRef
from app.providers.web.base import WebFetcher

API = "https://api.github.com/repos"
_HEADERS = {"Accept": "application/vnd.github+json"}


def _unavailable() -> AppError:
    return AppError("github_unavailable", "GitHub n’a pas pu être lu. Réessaie plus tard.", 502)


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
        try:
            result = await self._fetcher.fetch(
                f"{API}/{path}", content_types=("application/json",), headers=_HEADERS
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

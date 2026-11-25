"""Reading a GitHub repository through the public REST API (SPEC 10.2): `GET /repos/{o}/{r}` for the
metadata, `GET /repos/{o}/{r}/readme` for the README (JSON, `content` in base64 cut by line breaks,
`encoding: "base64"`). Without a token: 60 calls per hour per IP address, two per repository read
(D74). Both calls go through the safe `WebFetcher` (SSRF guard, rate limit).

Only `owner` and `repo`, validated by regular expression, go into the API URL: no other part of the
URL received is passed on."""

import base64
import binascii
import json
from typing import Any

from app.core.errors import AppError
from app.core.github_refs import github_repo as github_repo
from app.providers.pdf import base as pdf_limits
from app.providers.web.base import (
    GITHUB_UNREADABLE,
    TIMEOUT_MESSAGE,
    UrlForbidden,
    UrlUnreadable,
    WebDocument,
    WebFetcher,
)

API_ROOT = "https://api.github.com/repos"
_JSON = ("application/json",)
# Without `X-GitHub-Api-Version`: GitHub applies its default version, always supported
# (a dated version would eventually be removed and would answer 400).
_HEADERS = {"Accept": "application/vnd.github+json"}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _readme(payload: dict[str, Any]) -> str:
    if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        raise UrlUnreadable(GITHUB_UNREADABLE)
    try:
        raw = base64.b64decode("".join(payload["content"].split()), validate=True)
    except (binascii.Error, ValueError):
        raise UrlUnreadable(GITHUB_UNREADABLE) from None
    text = raw.decode("utf-8", errors="replace").strip()[: pdf_limits.MAX_TEXT_CHARS]
    if not text:
        raise UrlUnreadable(GITHUB_UNREADABLE)
    return text


class GithubReader:
    def __init__(self, fetcher: WebFetcher) -> None:
        self._fetcher = fetcher

    async def read(self, url: str) -> WebDocument:
        """README and metadata; any API failure (missing, limit reached, unexpected response) →
        `UrlUnreadable(GITHUB_UNREADABLE)`. A refused address (`UrlForbidden`) and the deadline
        pass through unchanged."""
        repo = github_repo(url)
        if repo is None:
            raise UrlUnreadable(GITHUB_UNREADABLE)
        endpoint = f"{API_ROOT}/{repo[0]}/{repo[1]}"
        meta = await self._json(endpoint)
        text = _readme(await self._json(endpoint + "/readme"))
        owner = meta.get("owner")
        return WebDocument(
            url=url,
            title=_text(meta.get("full_name")),
            text=text,
            author=_text(owner.get("login")) if isinstance(owner, dict) else None,
            date=_text(meta.get("pushed_at")),
            lang=None,
            description=_text(meta.get("description")),
        )

    async def _json(self, endpoint: str) -> dict[str, Any]:
        try:
            resource = await self._fetcher.fetch(endpoint, content_types=_JSON, headers=_HEADERS)
        except UrlForbidden:
            raise
        except UrlUnreadable as exc:
            if exc.message == TIMEOUT_MESSAGE:
                raise
            raise UrlUnreadable(GITHUB_UNREADABLE) from None
        except AppError:
            raise UrlUnreadable(GITHUB_UNREADABLE) from None
        try:
            payload = json.loads(resource.body)
        except (ValueError, RecursionError):
            raise UrlUnreadable(GITHUB_UNREADABLE) from None
        if not isinstance(payload, dict):
            raise UrlUnreadable(GITHUB_UNREADABLE)
        return payload

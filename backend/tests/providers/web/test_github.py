"""Lecture d'un dépôt GitHub par l'API publique (README, métadonnées), par le fetcher sûr."""

import base64
import json

import httpx
import pytest

from app.providers.web.base import GITHUB_UNREADABLE, UrlForbidden, UrlUnreadable
from app.providers.web.github import GithubReader, github_repo
from tests.providers.web.fetch_support import FakeResolver, Handler, fetcher_for, never, ok

README = "# Requests\n\nRequests est une bibliothèque HTTP élégante et simple pour Python.\n"
REPO = {
    "full_name": "psf/requests",
    "owner": {"login": "psf"},
    "pushed_at": "2026-10-30T12:00:00Z",
    "description": "A simple, yet elegant, HTTP library.",
}


def _b64(text: str) -> str:
    """Base64 coupé en lignes de 60 caractères, comme le rend l'API."""
    raw = base64.b64encode(text.encode()).decode()
    return "\n".join(raw[i : i + 60] for i in range(0, len(raw), 60))


def _json(payload: object, status: int = 200) -> httpx.Response:
    body = json.dumps(payload).encode()
    return ok(body, status=status, **{"content-type": "application/json; charset=utf-8"})


def _api(readme: httpx.Response | None = None, repo: httpx.Response | None = None) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.github.com"
        if request.url.path == "/repos/psf/requests":
            return repo or _json(REPO)
        if request.url.path == "/repos/psf/requests/readme":
            return readme or _json({"content": _b64(README), "encoding": "base64"})
        return _json({"message": "Not Found"}, 404)

    return handler


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/psf/requests", ("psf", "requests")),
        ("https://github.com/psf/requests.git", ("psf", "requests")),
        ("https://github.com/psf/requests/tree/main/docs", ("psf", "requests")),
        ("https://www.github.com/psf/requests?tab=readme#usage", ("psf", "requests")),
        ("http://GitHub.com/torvalds/linux/", ("torvalds", "linux")),
        ("https://github.com/settings/profile", None),
        ("https://github.com/orgs/psf", None),
        ("https://github.com/marketplace/actions", None),
        ("https://github.com/psf", None),
        ("https://github.com/", None),
        ("https://gitlab.com/a/b", None),
        ("https://github.com.evil.org/psf/requests", None),
        ("https://user:pw@github.com/psf/requests", None),
        ("ftp://github.com/psf/requests", None),
        ("https://github.com/psf/..", None),
        ("https://github.com/psf/.git", None),
        ("https://github.com/bad_owner/repo", None),
        (f"https://github.com/{'a' * 40}/repo", None),
        (f"https://github.com/psf/{'r' * 101}", None),
        ("pas une url", None),
    ],
)
def test_github_repo_forms(url: str, expected: tuple[str, str] | None) -> None:
    assert github_repo(url) == expected


async def test_github_reads_readme_and_metadata() -> None:
    seen: list[httpx.Request] = []
    fetcher, _ = fetcher_for(_api(), seen=seen)
    url = "https://github.com/psf/requests/tree/main"
    doc = await GithubReader(fetcher).read(url)
    assert doc.url == url and doc.text == README.strip()
    assert (doc.title, doc.author, doc.date) == ("psf/requests", "psf", "2026-10-30T12:00:00Z")
    assert doc.description == "A simple, yet elegant, HTTP library."
    assert [r.url.path for r in seen] == ["/repos/psf/requests", "/repos/psf/requests/readme"]
    assert all(r.headers["accept"] == "application/vnd.github+json" for r in seen)


async def test_github_tolerates_missing_metadata_fields() -> None:
    fetcher, _ = fetcher_for(_api(repo=_json({"owner": None, "description": 42})))
    doc = await GithubReader(fetcher).read("https://github.com/psf/requests")
    assert (doc.title, doc.author, doc.date, doc.description) == (None, None, None, None)
    assert doc.text == README.strip()


@pytest.mark.parametrize(
    "readme",
    [
        _json({"message": "Not Found"}, 404),
        _json({"message": "API rate limit exceeded"}, 403),
        _json({"content": "%%%pas du base64%%%", "encoding": "base64"}),
        _json({"content": _b64(README), "encoding": "utf-16"}),
        _json({"content": _b64("   \n  "), "encoding": "base64"}),
        _json(["liste"]),
        ok(b"{pas du json", **{"content-type": "application/json"}),
        ok(b"<html></html>", **{"content-type": "text/html"}),
    ],
    ids=["404", "limite", "base64", "encodage", "vide", "liste", "json", "html"],
)
async def test_github_missing_readme_is_unreadable(readme: httpx.Response) -> None:
    fetcher, _ = fetcher_for(_api(readme=readme))
    with pytest.raises(UrlUnreadable) as caught:
        await GithubReader(fetcher).read("https://github.com/psf/requests")
    assert caught.value.message == GITHUB_UNREADABLE and caught.value.__cause__ is None


async def test_github_missing_repo_is_unreadable() -> None:
    fetcher, _ = fetcher_for(_api(repo=_json({"message": "Not Found"}, 404)))
    with pytest.raises(UrlUnreadable) as caught:
        await GithubReader(fetcher).read("https://github.com/psf/requests")
    assert caught.value.message == GITHUB_UNREADABLE


async def test_github_non_repo_url_is_unreadable_without_request() -> None:
    fetcher, _ = fetcher_for(never)
    with pytest.raises(UrlUnreadable) as caught:
        await GithubReader(fetcher).read("https://github.com/settings")
    assert caught.value.message == GITHUB_UNREADABLE


async def test_github_api_goes_through_the_ssrf_guard() -> None:
    fetcher, _ = fetcher_for(never, FakeResolver({"api.github.com": ["127.0.0.1"]}))
    with pytest.raises(UrlForbidden):
        await GithubReader(fetcher).read("https://github.com/psf/requests")

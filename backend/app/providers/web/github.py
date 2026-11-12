"""Lecture d'un dépôt GitHub par l'API REST publique (SPEC 10.2) : `GET /repos/{o}/{r}` pour les
métadonnées, `GET /repos/{o}/{r}/readme` pour le README (JSON, `content` en base64 coupé de
retours à la ligne, `encoding: "base64"`). Sans jeton : 60 appels par heure et par adresse IP,
deux par dépôt lu (D74). Les deux appels passent par le `WebFetcher` sûr (garde SSRF, débit).

Seuls `owner` et `repo`, validés par expression régulière, entrent dans l'URL de l'API : aucune
autre partie de l'URL reçue n'est transmise."""

import base64
import binascii
import json
import re
from typing import Any
from urllib.parse import urlsplit

from app.core.errors import AppError
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
_HOSTS = frozenset({"github.com", "www.github.com"})
_OWNER = re.compile(r"[A-Za-z0-9-]{1,39}")
_REPO = re.compile(r"[A-Za-z0-9._-]{1,100}")
_JSON = ("application/json",)
# Sans `X-GitHub-Api-Version` : GitHub applique sa version par défaut, toujours prise en charge
# (une version datée finirait par être retirée et répondrait 400).
_HEADERS = {"Accept": "application/vnd.github+json"}
# Premiers segments de github.com qui ne sont pas un compte (pages du site).
_RESERVED = frozenset(
    {
        "about", "account", "apps", "blog", "codespaces", "collections", "contact",
        "customer-stories", "dashboard", "enterprise", "events", "explore", "features",
        "issues", "join", "login", "logout", "marketplace", "new", "notifications",
        "organizations", "orgs", "pricing", "pulls", "readme", "search", "security",
        "sessions", "settings", "site", "sponsors", "team", "topics", "trending", "users",
    }
)  # fmt: skip


def github_repo(url: str) -> tuple[str, str] | None:
    """`(owner, repo)` d'une URL `https://github.com/<owner>/<repo>[/tree/...]`, `.git` retiré ;
    `None` pour toute autre URL (page du site, autre hôte, identifiants, nom invalide)."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or host not in _HOSTS:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    segments = [s for s in parts.path.split("/") if s]
    # Racine du dépôt ou `tree/<branche>` seulement : une issue, une PR ou un fichier citeraient
    # leur URL avec le texte du README (revue 3.4) ; ils restent au lecteur de pages.
    if len(segments) < 2 or (len(segments) > 2 and segments[2] != "tree"):
        return None
    owner, repo = segments[0], segments[1].removesuffix(".git")
    if owner.lower() in _RESERVED or repo in ("", ".", ".."):
        return None
    if not (_OWNER.fullmatch(owner) and _REPO.fullmatch(repo)):
        return None
    return owner, repo


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
        """README et métadonnées ; tout échec de l'API (absent, limite atteinte, réponse
        inattendue) → `UrlUnreadable(GITHUB_UNREADABLE)`. Une adresse refusée (`UrlForbidden`)
        et le délai dépassé passent tels quels."""
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

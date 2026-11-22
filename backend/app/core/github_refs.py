"""Références canoniques aux dépôts GitHub publics."""

import re
from urllib.parse import urlsplit

_HOSTS = frozenset({"github.com", "www.github.com"})
_OWNER = re.compile(r"[A-Za-z0-9-]{1,39}")
_REPO = re.compile(r"[A-Za-z0-9._-]{1,100}")
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

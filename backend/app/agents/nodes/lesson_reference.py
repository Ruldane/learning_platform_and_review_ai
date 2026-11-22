"""Comparaison des adresses citées dans une leçon et des pages lues."""

from urllib.parse import urlsplit, urlunsplit


def source_url_key(url: str) -> str | None:
    """Clé tolérante d'une adresse : hôte en minuscules, sans `/` final ni fragment."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))

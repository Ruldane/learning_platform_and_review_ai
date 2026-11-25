"""Compares the URLs cited in a lesson with the pages read."""

from urllib.parse import urlsplit, urlunsplit


def source_url_key(url: str) -> str | None:
    """Lenient key for a URL: lowercase host, no trailing `/` and no fragment."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))

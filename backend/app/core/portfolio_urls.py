"""Origine explicite et chemin unique de la publication statique."""

from urllib.parse import urlsplit

PUBLIC_PATH = "/api/v1/public/portfolios/"
_LOCAL = frozenset({"localhost", "127.0.0.1", "::1"})
_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_origin(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    clean = value.strip()
    try:
        parts = urlsplit(clean)
        host = parts.hostname
        port = parts.port
    except ValueError as error:
        raise ValueError("Origine publique invalide.") from error
    if (
        not host
        or not host.isascii()
        or any(char.isspace() or char == "\\" for char in clean)
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
        or (parts.scheme != "https" and not (parts.scheme == "http" and host in _LOCAL))
    ):
        raise ValueError("Configure une origine HTTPS, ou une adresse locale pour les tests.")
    authority = f"[{host}]" if ":" in host else host
    if port is not None and port != _DEFAULT_PORTS[parts.scheme]:
        authority = f"{authority}:{port}"
    return f"{parts.scheme}://{authority}"


def matches_public_host(origin: str | None, authority: str) -> bool:
    if not origin or not authority or any(char.isspace() or char == "\\" for char in authority):
        return False
    try:
        configured = urlsplit(origin)
        incoming = urlsplit(f"//{authority}")
        default_port = _DEFAULT_PORTS.get(configured.scheme)
        configured_port = configured.port
        incoming_port = incoming.port
        return (
            configured.hostname is not None
            and incoming.hostname == configured.hostname
            and incoming.username is None
            and incoming.password is None
            and not (incoming.path or incoming.query or incoming.fragment)
            and (incoming_port if incoming_port is not None else default_port)
            == (configured_port if configured_port is not None else default_port)
        )
    except ValueError:
        return False


def public_url(origin: str | None, slug: str) -> str | None:
    return f"{origin}{PUBLIC_PATH}{slug}" if origin else None


def no_origin() -> None:
    return None

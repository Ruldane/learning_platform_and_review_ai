"""PKCE (RFC 7636), S256 method: the verifier stays on the server; only its fingerprint is sent."""

import base64
import hashlib
import secrets


def new_verifier() -> str:
    """A random verifier: 86 characters, within the RFC's range of 43 to 128."""
    return secrets.token_urlsafe(64)


def challenge(verifier: str) -> str:
    """`base64url(sha256(verifier))` without the `=` padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

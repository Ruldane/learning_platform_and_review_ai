"""PKCE (RFC 7636), méthode S256 : le vérificateur reste côté serveur, seule son empreinte part."""

import base64
import hashlib
import secrets


def new_verifier() -> str:
    """Un vérificateur aléatoire : 86 caractères, dans la plage de 43 à 128 de la RFC."""
    return secrets.token_urlsafe(64)


def challenge(verifier: str) -> str:
    """`base64url(sha256(verifier))` sans le remplissage `=`."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

"""Port de la connexion OpenID Connect (phase 9, P5) : l'identité rendue et l'erreur unique.

Aucun message d'erreur ni journal ne cite un code d'autorisation, un jeton, un `state`, un
vérificateur PKCE, un e-mail ou un `sub` (SPEC 17.2) : l'erreur ne porte que son code."""

from dataclasses import dataclass
from typing import Protocol

OIDC_ERROR_CODES = ("access_denied", "google_unavailable", "token_invalid")


@dataclass(frozen=True)
class OidcIdentity:
    sub: str
    email: str
    # Rendu tel quel par le fournisseur : le refus d'un e-mail non vérifié est décidé par le
    # service de connexion, pas par le port.
    email_verified: bool
    name: str


class OidcError(Exception):
    """Échec de la connexion : `access_denied`, `google_unavailable` ou `token_invalid`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class OidcProvider(Protocol):
    def authorization_url(
        self, *, state: str, code_challenge: str, nonce: str, login_hint: str | None
    ) -> str:
        """L'adresse du fournisseur où envoyer le navigateur."""
        ...

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> OidcIdentity:
        """Échange le code contre l'identité ; `OidcError` si le fournisseur refuse ou tombe."""
        ...

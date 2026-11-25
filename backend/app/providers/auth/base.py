"""OpenID Connect sign-in port (phase 9, P5): the identity returned and the single error.

No error message or log quotes an authorization code, a token, a `state`, a PKCE
verifier, an email or a `sub` (SPEC 17.2): the error only carries its code."""

from dataclasses import dataclass
from typing import Protocol

OIDC_ERROR_CODES = ("access_denied", "google_unavailable", "token_invalid")


@dataclass(frozen=True)
class OidcIdentity:
    sub: str
    email: str
    # Returned as is by the provider: the refusal of an unverified email is decided by the
    # sign-in service, not by the port.
    email_verified: bool
    name: str


class OidcError(Exception):
    """Sign-in failure: `access_denied`, `google_unavailable` or `token_invalid`."""

    def __init__(self, code: str) -> None:
        if code not in OIDC_ERROR_CODES:
            raise ValueError("unknown OIDC error code")
        super().__init__(code)
        self.code = code


class OidcProvider(Protocol):
    def authorization_url(
        self, *, state: str, code_challenge: str, nonce: str, login_hint: str | None
    ) -> str:
        """The provider's address where to send the browser."""
        ...

    async def exchange(self, *, code: str, code_verifier: str, nonce: str) -> OidcIdentity:
        """Exchanges the code for the identity; `OidcError` if the provider refuses or is down."""
        ...

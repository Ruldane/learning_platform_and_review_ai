"""Sign-in (SPEC 14.2, 17.1, phase 9): the current user, Google sign-in (OpenID Connect,
authorization code with PKCE), taking over the local space and sign-out.

The session cookie (`tremplin_session`) is opaque, `HttpOnly` and `SameSite=Lax`; only its
SHA-256 is kept. No e-mail, name, `sub`, code, `state`, token or `login_hint` is logged. No
redirect targets an address received as a parameter."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.config import Settings
from app.core.deps import CurrentUserDep, Db, get_cipher, get_providers
from app.core.errors import AppError
from app.features.auth.schemas import ClaimIn, MeOut
from app.features.auth.service import AuthService, claim, cookies, sessions
from app.features.auth.service.login import CallbackOutcome, finish_login, start_login
from app.providers.auth.base import OidcProvider

router = APIRouter(prefix="/auth", tags=["auth"])

_NO_GOOGLE: dict[int | str, dict[str, Any]] = {404: {"description": "`google_auth_disabled`"}}


def _oidc(request: Request) -> OidcProvider:
    """The application's Google sign-in; local mode: 404 `google_auth_disabled`."""
    oidc = get_providers(request).oidc
    if oidc is None:
        raise AppError("google_auth_disabled", "Google sign-in is disabled.", 404)
    return oidc


def _secure(settings: Settings) -> bool:
    """`Secure` when the return address (where the cookies are set) is https."""
    return settings.google_redirect_uri.startswith("https://")


def _destination(settings: Settings, outcome: CallbackOutcome) -> str:
    """Always a front-end address set by the configuration, never a received parameter (P10)."""
    front = settings.frontend_url.rstrip("/")
    if outcome.kind == "signed_in":
        return f"{front}/"
    if outcome.kind == "claim":
        return f"{front}/login/claim"
    return f"{front}/login?error={outcome.error}"


@router.get(
    "/me",
    response_model=MeOut,
    responses={401: {"description": "`auth_required`: Google mode, no valid session"}},
)
async def me(request: Request, current: CurrentUserDep, db: Db) -> MeOut:
    """The signed-in user (local mode: the single user)."""
    user = await AuthService(db).get_user(current.id)
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        auth_mode=request.app.state.settings.auth_mode,
    )


@router.get(
    "/google/login",
    response_class=RedirectResponse,
    status_code=302,
    responses={302: {"description": "Redirection vers Google"}, **_NO_GOOGLE},
)
async def google_login(request: Request, login_hint: str | None = None) -> RedirectResponse:
    """Starts the sign-in: sets the `tremplin_oauth` cookie (`state`, PKCE verifier, `nonce`,
    encrypted, 10 minutes) and redirects to Google. `login_hint` (optional) pre-fills the
    address. Local mode: 404 `google_auth_disabled`."""
    settings: Settings = request.app.state.settings
    url, pending = start_login(_oidc(request), get_cipher(request), login_hint)
    response = RedirectResponse(url, status_code=302)
    cookies.set_oauth_cookie(response, pending, secure=_secure(settings))
    return response


@router.get(
    "/google/callback",
    response_class=RedirectResponse,
    status_code=302,
    responses={
        302: {
            "description": "Redirects to `/` after sign-in, `/login/claim` to choose whether "
            "to claim existing data, or `/login?error=<code>` if sign-in fails."
        },
        **_NO_GOOGLE,
    },
)
async def google_callback(
    request: Request,
    db: Db,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Return from Google: checks the `state`, exchanges the code, verifies the identity token
    (issuer, audience, `nonce`, verified address, `ALLOWED_EMAILS`) then opens the session or
    offers to take over the local space. Always a redirect to the front end, never an error
    displayed by the API."""
    settings: Settings = request.app.state.settings
    outcome = await finish_login(
        db,
        _oidc(request),
        get_cipher(request),
        settings,
        code=code,
        state=state,
        error=error,
        oauth_cookie=request.cookies.get(cookies.OAUTH_COOKIE),
        now=datetime.now(UTC),
    )
    response = RedirectResponse(_destination(settings, outcome), status_code=302)
    secure = _secure(settings)
    cookies.clear_oauth_cookie(response, secure=secure)
    if outcome.kind == "signed_in" and outcome.token:
        days = settings.session_days
        cookies.set_session_cookie(response, outcome.token, days=days, secure=secure)
    elif outcome.kind == "claim" and outcome.claim_cookie:
        cookies.set_claim_cookie(response, outcome.claim_cookie, secure=secure)
    return response


@router.post(
    "/google/claim",
    response_model=MeOut,
    responses={
        409: {
            "description": "`claim_expired` (the `tremplin_claim` cookie is missing or older than "
            '10 minutes, or "empty space" was already chosen: the account exists, signing in '
            "again is enough, or the address is no longer named in `ALLOWED_EMAILS`) or "
            "`local_already_claimed` (the local space already has an owner)"
        },
        **_NO_GOOGLE,
    },
)
async def google_claim(body: ClaimIn, request: Request, response: Response, db: Db) -> MeOut:
    """The choice of the very first sign-in: `take_local` attaches the Google identity to the
    local space, `fresh` creates an empty space. Opens the session (cookie set) and returns the
    user."""
    _oidc(request)  # mode local : 404 `google_auth_disabled`
    settings: Settings = request.app.state.settings
    user = await claim.claim(
        db,
        get_cipher(request),
        request.cookies.get(cookies.CLAIM_COOKIE),
        body.choice,
        allowed_emails=settings.allowed_emails,
    )
    token = await sessions.open_session(
        db, user.id, now=datetime.now(UTC), days=settings.session_days
    )
    secure = _secure(settings)
    cookies.set_session_cookie(response, token, days=settings.session_days, secure=secure)
    cookies.clear_claim_cookie(response, secure=secure)
    return MeOut(id=user.id, email=user.email, name=user.name, auth_mode=settings.auth_mode)


@router.post("/logout", status_code=204, response_class=Response)
async def logout(request: Request, db: Db) -> Response:
    """Deletes the cookie's session and clears the cookie (same path as when it was set). No
    effect in local mode; without a session, 204 as well."""
    response = Response(status_code=204)
    settings: Settings = request.app.state.settings
    if settings.auth_mode == "google":
        token = request.cookies.get(cookies.SESSION_COOKIE)
        if token:
            await sessions.close_session(db, token)
        cookies.clear_session_cookie(response, secure=_secure(settings))
    return response

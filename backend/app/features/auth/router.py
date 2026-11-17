"""Connexion (SPEC 14.2, 17.1, phase 9) : l'utilisateur courant, la connexion par Google (OpenID
Connect, code d'autorisation avec PKCE), la reprise de l'espace local et la déconnexion.

Le cookie de session (`tremplin_session`) est opaque, `HttpOnly` et `SameSite=Lax` ; seul son
SHA-256 est gardé. Ni e-mail, ni nom, ni `sub`, ni code, ni `state`, ni jeton, ni `login_hint` ne
sont journalisés. Aucune redirection ne vise une adresse reçue en paramètre."""

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
    """La connexion Google de l'application ; mode local : 404 `google_auth_disabled`."""
    oidc = get_providers(request).oidc
    if oidc is None:
        raise AppError("google_auth_disabled", "La connexion Google n'est pas activée.", 404)
    return oidc


def _secure(settings: Settings) -> bool:
    """`Secure` quand l'adresse de retour (où les cookies sont posés) est en https."""
    return settings.google_redirect_uri.startswith("https://")


def _destination(settings: Settings, outcome: CallbackOutcome) -> str:
    """Toujours une adresse du front fixée par la configuration, jamais reçue en paramètre (P10)."""
    front = settings.frontend_url.rstrip("/")
    if outcome.kind == "signed_in":
        return f"{front}/"
    if outcome.kind == "claim":
        return f"{front}/connexion/reprise"
    return f"{front}/connexion?erreur={outcome.error}"


@router.get(
    "/me",
    response_model=MeOut,
    responses={401: {"description": "`auth_required` : mode Google, aucune session valide"}},
)
async def me(request: Request, current: CurrentUserDep, db: Db) -> MeOut:
    """L'utilisateur connecté (mode local : l'utilisateur unique)."""
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
    """Commence la connexion : pose le témoin `tremplin_oauth` (`state`, vérificateur PKCE,
    `nonce`, chiffrés, 10 minutes) et renvoie vers Google. `login_hint` (facultatif) préremplit
    l'adresse. Mode local : 404 `google_auth_disabled`."""
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
            "description": "Redirection vers le front : `/` (connectée), `/connexion/reprise` "
            "(choix de la reprise) ou `/connexion?erreur=<code>` (échec, rien n'est créé)"
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
    """Retour de Google : contrôle le `state`, échange le code, vérifie le jeton d'identité
    (émetteur, audience, `nonce`, adresse vérifiée, `ALLOWED_EMAILS`) puis ouvre la session ou
    propose la reprise de l'espace local. Toujours une redirection vers le front, jamais une
    erreur affichée par l'API."""
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
            "description": "`claim_expired` (le témoin `tremplin_claim` manque ou a plus de "
            "10 minutes, ou « espace vide » a déjà été choisi : le compte existe, il suffit de "
            "se reconnecter) ou `local_already_claimed` (l'espace local a déjà un propriétaire)"
        },
        **_NO_GOOGLE,
    },
)
async def google_claim(body: ClaimIn, request: Request, response: Response, db: Db) -> MeOut:
    """Le choix de la toute première connexion : `take_local` attache l'identité Google à
    l'espace local, `fresh` crée un espace vide. Ouvre la session (cookie posé) et rend
    l'utilisateur."""
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
    """Supprime la session du cookie et efface le cookie (même chemin que la pose). Sans effet en
    mode local ; sans session, 204 aussi."""
    response = Response(status_code=204)
    settings: Settings = request.app.state.settings
    if settings.auth_mode == "google":
        token = request.cookies.get(cookies.SESSION_COOKIE)
        if token:
            await sessions.close_session(db, token)
        cookies.clear_session_cookie(response, secure=_secure(settings))
    return response

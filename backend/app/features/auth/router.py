"""Connexion (SPEC 14.2, 17.1, phase 9) : l'utilisateur courant, la connexion par Google (OpenID
Connect, code d'autorisation avec PKCE), la reprise de l'espace local et la déconnexion.

Le cookie de session (`tremplin_session`) est opaque, `HttpOnly` et `SameSite=Lax` ; seul son
SHA-256 est gardé. Ni e-mail, ni nom, ni `sub`, ni code, ni `state`, ni jeton, ni `login_hint` ne
sont journalisés. Aucune redirection ne vise une adresse reçue en paramètre."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.core.deps import CurrentUserDep, Db
from app.core.errors import AppError
from app.features.auth.schemas import ClaimIn, MeOut
from app.features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_NO_GOOGLE: dict[int | str, dict[str, Any]] = {404: {"description": "`google_auth_disabled`"}}


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
async def google_login(
    login_hint: Annotated[str | None, Query(max_length=320)] = None,
) -> RedirectResponse:
    """Commence la connexion : pose le témoin `tremplin_oauth` (`state`, vérificateur PKCE,
    `nonce`, chiffrés, 10 minutes) et renvoie vers Google. `login_hint` (facultatif) préremplit
    l'adresse. Mode local : 404 `google_auth_disabled`."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)


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
    code: Annotated[str | None, Query(max_length=2048)] = None,
    state: Annotated[str | None, Query(max_length=2048)] = None,
    error: Annotated[str | None, Query(max_length=256)] = None,
) -> RedirectResponse:
    """Retour de Google : contrôle le `state`, échange le code, vérifie le jeton d'identité
    (émetteur, audience, `nonce`, adresse vérifiée, `ALLOWED_EMAILS`) puis ouvre la session ou
    propose la reprise de l'espace local. Toujours une redirection vers le front, jamais une
    erreur affichée par l'API."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)


@router.post(
    "/google/claim",
    response_model=MeOut,
    responses={
        409: {
            "description": "`claim_expired` (le témoin `tremplin_claim` manque ou a plus de "
            "10 minutes) ou `local_already_claimed` (l'espace local a déjà un propriétaire)"
        },
        **_NO_GOOGLE,
    },
)
async def google_claim(body: ClaimIn, response: Response) -> MeOut:
    """Le choix de la toute première connexion : `take_local` attache l'identité Google à
    l'espace local, `fresh` crée un espace vide. Ouvre la session (cookie posé) et rend
    l'utilisateur."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)


@router.post("/logout", status_code=204, response_class=Response)
async def logout(response: Response) -> Response:
    """Supprime la session du cookie et efface le cookie (même chemin que la pose). Sans effet en
    mode local ; sans session, 204 aussi."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)

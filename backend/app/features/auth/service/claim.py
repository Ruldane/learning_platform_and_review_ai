"""Reprise de l'espace local (P9, 17.1) : le tout premier compte Google peut reprendre l'espace créé
en mode local ou repartir d'un espace vide.

- Proposée **seulement** quand aucun compte Google n'existe encore ET que l'utilisateur `local`
  existe (`claim_offered`) ET que `ALLOWED_EMAILS` est une liste explicite qui nomme l'adresse
  (jamais avec `*` : la première personne venue prendrait des données qui ne sont pas les siennes) :
  un second compte ne la voit jamais, ni après un premier choix.
- « Reprendre » (`take_local`) **attache l'identité à la ligne `local`** : même `id`, donc aucune
  donnée déplacée (base, index, fichiers, points de reprise). Un seul UPDATE conditionnel décide
  qui est propriétaire : le perdant d'une course reçoit 409 `local_already_claimed`.
- « Espace vide » (`fresh`) crée un utilisateur neuf ; l'espace local reste intact.
- Le choix se fait avec le témoin `tremplin_claim` (`{sub, email, name}` chiffré, 10 minutes,
  posé par le callback) : absent, trafiqué ou trop vieux = 409 `claim_expired`.

Ni e-mail, ni nom, ni `sub`, ni contenu du témoin n'est journalisé : des identifiants seulement."""

import json
import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import Cipher
from app.db.models.accounts import User
from app.features.auth.repository import UserRepository
from app.features.auth.service.allowlist import explicitly_allowed
from app.features.auth.service.cookies import OAUTH_COOKIE_SECONDS

logger = logging.getLogger(__name__)

Choice = Literal["take_local", "fresh"]


@dataclass(frozen=True)
class ClaimIdentity:
    """L'identité Google contrôlée par le callback, gardée dans le témoin `tremplin_claim`."""

    sub: str
    email: str
    name: str


def _expired() -> AppError:
    return AppError("claim_expired", "Le choix a expiré : reconnecte-toi avec Google.", 409)


def _taken() -> AppError:
    return AppError("local_already_claimed", "L'espace local a déjà un propriétaire.", 409)


def seal_identity(cipher: Cipher, identity: ClaimIdentity) -> str:
    """La valeur du témoin `tremplin_claim`."""
    payload = {"sub": identity.sub, "email": identity.email, "name": identity.name}
    return cipher.encrypt(json.dumps(payload))


def open_identity(cipher: Cipher, raw: str | None) -> ClaimIdentity | None:
    """L'identité du témoin, `None` s'il manque, est trafiqué ou a plus de 10 minutes."""
    if not raw:
        return None
    try:
        data = json.loads(cipher.decrypt(raw, ttl=OAUTH_COOKIE_SECONDS))
    except (AppError, ValueError):  # illisible ou périmé (`SecretUnreadable`), ou pas du JSON
        return None
    if not isinstance(data, dict) or not all(
        isinstance(data.get(key), str) for key in ("sub", "email", "name")
    ):
        return None
    return ClaimIdentity(sub=data["sub"], email=data["email"], name=data["name"])


async def claim_offered(db: AsyncSession) -> bool:
    """Vrai si la reprise doit être proposée : aucun compte Google, et l'utilisateur `local`
    est là (jamais repris : une fois repris il porte un e-mail, `get_local` ne le rend plus)."""
    users = UserRepository(db)
    return not await users.any_google_user() and await users.get_local() is not None


async def claim(
    db: AsyncSession,
    cipher: Cipher,
    claim_cookie: str | None,
    choice: Choice,
    *,
    allowed_emails: str | None,
) -> User:
    """Applique le choix du tout premier compte Google et rend son utilisateur (la session est
    ouverte par l'appelant, dans la même transaction). 409 `claim_expired` : témoin absent,
    trafiqué ou vieux, ou adresse plus nommée dans `ALLOWED_EMAILS` (retirée, ou liste devenue
    `*`) ; 409
    `local_already_claimed` : l'espace local est déjà repris, ou un compte Google existe déjà
    (autre onglet, autre compte, premier choix « espace vide »). Un témoin rejoué avec `fresh`
    (compte déjà créé, double clic) : 409 `claim_expired`, jamais « déjà un propriétaire »."""
    identity = open_identity(cipher, claim_cookie)
    if identity is None or not explicitly_allowed(identity.email, allowed_emails):
        raise _expired()
    users = UserRepository(db)
    if await users.get_by_google_sub(identity.sub) is not None:
        # Témoin rejoué : ce compte existe déjà, la connexion normale suffit. `fresh` (double clic
        # sur « Espace vide ») : le choix est fait, pas de propriétaire de l'espace local en jeu.
        raise _expired() if choice == "fresh" else _taken()
    if choice == "take_local":
        user = await _take_local(users, identity)
        logger.info("espace local repris par l'utilisateur %s", user.id)
    else:
        user = await _fresh(db, users, identity)
        logger.info("espace vide créé pour l'utilisateur %s", user.id)
    return user


async def _take_local(users: UserRepository, identity: ClaimIdentity) -> User:
    local = await users.get_local()
    if local is None:
        raise _taken()
    try:
        attached = await users.attach_identity(
            local.id, identity.sub, identity.email, identity.name
        )
    except IntegrityError as exc:  # adresse déjà portée : le callback aurait dû la refuser
        raise _expired() from exc
    if not attached:
        raise _taken()
    return local


async def _fresh(db: AsyncSession, users: UserRepository, identity: ClaimIdentity) -> User:
    try:
        async with db.begin_nested():  # un doublon (deux onglets) ne défait pas la transaction
            return await users.add_google(
                sub=identity.sub, email=identity.email, name=identity.name
            )
    except IntegrityError as exc:
        # Même `sub` créé entre-temps par l'autre onglet (le choix est déjà fait) ou adresse prise
        # par un autre compte : dans les deux cas, reconnexion.
        raise _expired() from exc

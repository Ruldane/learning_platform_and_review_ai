"""Taking over the local space (P9, 17.1): the very first Google account can take over the space
created in local mode or start from an empty space.

- Offered **only** when no Google account exists yet AND the `local` user exists
  (`claim_offered`) AND `ALLOWED_EMAILS` is an explicit list that names the address (never with
  `*`: the first person to come along would take data that is not theirs): a second account
  never sees it, nor after a first choice.
- "Take over" (`take_local`) **attaches the identity to the `local` row**: same `id`, so no data
  moved (database, index, files, checkpoints). A single conditional UPDATE decides who is the
  owner: the loser of a race gets 409 `local_already_claimed`.
- "Empty space" (`fresh`) creates a new user; the local space stays intact. A replayed `fresh`
  (double click) or one lost in a race finds the account already created: 409 `claim_expired`
  (signing in again settles everything), never a second account nor `local_already_claimed`.
- The choice is made with the `tremplin_claim` cookie (`{sub, email, name}` encrypted,
  10 minutes, set by the callback): missing, tampered with or too old = 409 `claim_expired`.

No e-mail, name, `sub` or cookie content is logged: ids only."""

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
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

Choice = Literal["take_local", "fresh"]


@dataclass(frozen=True)
class ClaimIdentity:
    """The Google identity checked by the callback, kept in the `tremplin_claim` cookie."""

    sub: str
    email: str
    name: str


def _expired() -> AppError:
    return AppError("claim_expired", "This choice expired. Sign in with Google again.", 409)


def _taken() -> AppError:
    return AppError("local_already_claimed", "The local workspace already has an owner.", 409)


def seal_identity(cipher: Cipher, identity: ClaimIdentity) -> str:
    """The value of the `tremplin_claim` cookie."""
    payload = {"sub": identity.sub, "email": identity.email, "name": identity.name}
    return cipher.encrypt(json.dumps(payload))


def open_identity(cipher: Cipher, raw: str | None) -> ClaimIdentity | None:
    """The cookie's identity, `None` if it is missing, tampered with or older than 10 minutes."""
    if not raw:
        return None
    try:
        data = json.loads(cipher.decrypt(raw, ttl=OAUTH_COOKIE_SECONDS))
    except (AppError, ValueError):  # unreadable or expired (`SecretUnreadable`), or not JSON
        return None
    if not isinstance(data, dict) or not all(
        isinstance(data.get(key), str) for key in ("sub", "email", "name")
    ):
        return None
    return ClaimIdentity(sub=data["sub"], email=data["email"], name=data["name"])


async def claim_offered(db: AsyncSession) -> bool:
    """True if the takeover must be offered: no Google account, and the `local` user is there
    (never taken over: once taken over it carries an e-mail, `get_local` no longer returns it)."""
    users = UserRepository(db)
    if await users.any_google_user():
        return False
    local = await users.get_local()
    return local is not None and not await users.local_claim_closed(local.id)


async def close_claim(db: AsyncSession, users: UserRepository) -> None:
    """As soon as a first Google account is born ("Empty space" or sign-in without an offer; a
    takeover consumes the `local` row itself), the takeover is closed for good: the fact is kept
    in the settings of the `local` row, which a Google account's "Delete everything" never
    erases (review 9.R, B-I1)."""
    local = await users.get_local()
    if local is not None:
        await SettingsService(db, local.id).close_local_claim()


async def claim(
    db: AsyncSession,
    cipher: Cipher,
    claim_cookie: str | None,
    choice: Choice,
    *,
    allowed_emails: str | None,
) -> User:
    """Applies the choice of the very first Google account and returns its user (the session is
    opened by the caller, in the same transaction). 409 `claim_expired`: cookie missing,
    tampered with or old, or address no longer named in `ALLOWED_EMAILS` (removed, or list
    become `*`); 409 `local_already_claimed`: the local space is already taken over, or a Google
    account already exists (another tab, another account, first choice "empty space"). A cookie
    replayed with `fresh` (account already created, double click): 409 `claim_expired`, never
    "already an owner"."""
    identity = open_identity(cipher, claim_cookie)
    if identity is None or not explicitly_allowed(identity.email, allowed_emails):
        raise _expired()
    users = UserRepository(db)
    if await users.get_by_google_sub(identity.sub) is not None:
        # Cookie replayed: this account already exists, the normal sign-in is enough. `fresh`
        # (double click on "Empty space"): the choice is made, no local-space owner at stake.
        raise _expired() if choice == "fresh" else _taken()
    if choice == "take_local":
        user = await _take_local(users, identity)
        logger.info("local space taken over by user %s", user.id)
    else:
        user = await _fresh(db, users, identity)
        logger.info("empty space created for user %s", user.id)
    return user


async def _take_local(users: UserRepository, identity: ClaimIdentity) -> User:
    local = await users.get_local()
    if local is None:
        raise _taken()
    try:
        attached = await users.attach_identity(
            local.id, identity.sub, identity.email, identity.name
        )
    except IntegrityError as exc:  # address already used: the callback should have refused it
        raise _expired() from exc
    if not attached:
        raise _taken()
    return local


async def _fresh(db: AsyncSession, users: UserRepository, identity: ClaimIdentity) -> User:
    # Before the savepoint: the transaction starts with a write, never with a read followed by
    # a write (SQLite would answer "database is locked" to a race).
    await close_claim(db, users)
    try:
        async with db.begin_nested():  # a duplicate (two tabs) does not undo the transaction
            return await users.add_google(
                sub=identity.sub, email=identity.email, name=identity.name
            )
    except IntegrityError as exc:
        # Same `sub` created meanwhile by the other tab (the choice is already made) or address
        # taken by another account: in both cases, sign in again.
        raise _expired() from exc

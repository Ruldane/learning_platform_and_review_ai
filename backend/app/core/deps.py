from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import Cipher

if TYPE_CHECKING:  # évite un import à l'exécution : la composition vit dans app/bootstrap.py
    from app.bootstrap import Providers
    from app.providers.llm.factory import LlmFactory


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Session de la requête : commit en fin de requête, rollback sur erreur."""
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


# `scope="function"` : le code après `yield` (le commit) s'exécute AVANT l'envoi de la réponse.
# Avec la portée « request » par défaut, un échec de commit serait signalé après un 200 déjà
# parti, et le client pourrait lire avant que la donnée ne soit commitée. À utiliser partout.
Db = Annotated[AsyncSession, Depends(get_db, scope="function")]


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


def get_current_user(request: Request) -> CurrentUser:
    """Utilisateur de la requête. Mode `local` : l'utilisateur unique créé au démarrage.

    Mode `google` : la vraie connexion arrive en phase 9, d'ici là toute route protégée est en 401.
    """
    if request.app.state.settings.auth_mode == "local":
        return CurrentUser(id=request.app.state.local_user_id, email=None)
    raise AppError("auth_required", "Connexion requise.", 401)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_providers(request: Request) -> "Providers":
    """Services externes assemblés au démarrage par `app/bootstrap.py`."""
    providers: Providers = request.app.state.providers
    return providers


def get_llm_factory(request: Request) -> "LlmFactory":
    """Fabrique des modèles de chat (seul point d'instanciation des LLM)."""
    return get_providers(request).llm_factory


def get_cipher(request: Request) -> Cipher:
    cipher: Cipher = request.app.state.cipher
    return cipher

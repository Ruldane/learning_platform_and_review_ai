from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError


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

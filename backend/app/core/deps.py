from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.agents.runtime.lifespan import AgentRuntime
from app.core.errors import AppError
from app.core.providers import Providers
from app.core.security import Cipher
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


# Les dépendances ci-dessous prennent `HTTPConnection` (parent commun de `Request` et
# `WebSocket`) : FastAPI n'injecte pas `Request` sur une route WebSocket (flux de la phase 1).


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


def get_current_user(conn: HTTPConnection) -> CurrentUser:
    """Utilisateur de la requête. Mode `local` : l'utilisateur unique créé au démarrage.

    Mode `google` : la vraie connexion arrive en phase 9, d'ici là toute route protégée est en 401.
    """
    if conn.app.state.settings.auth_mode == "local":
        return CurrentUser(id=conn.app.state.local_user_id, email=None)
    raise AppError("auth_required", "Connexion requise.", 401)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_providers(conn: HTTPConnection) -> Providers:
    """Services externes assemblés au démarrage par `app/bootstrap.py`."""
    providers: Providers = conn.app.state.providers
    return providers


def get_llm_factory(conn: HTTPConnection) -> LlmFactory:
    """Fabrique des modèles de chat (seul point d'instanciation des LLM)."""
    return get_providers(conn).llm_factory


def get_cipher(conn: HTTPConnection) -> Cipher:
    cipher: Cipher = conn.app.state.cipher
    return cipher


def get_runtime(conn: HTTPConnection) -> AgentRuntime:
    """Moteur d'agents (bus, runner) ouvert par le lifespan (`app.agents.runtime.lifespan`)."""
    runtime: AgentRuntime = conn.app.state.runtime
    return runtime


RuntimeDep = Annotated[AgentRuntime, Depends(get_runtime)]

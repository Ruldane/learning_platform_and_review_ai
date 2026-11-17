from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.agents.runtime.handle import AgentRuntime
from app.core.caller import MCP_IDENTITY
from app.core.errors import AppError
from app.core.providers import Providers, PublishingProviders
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


class Authenticator(Protocol):
    """Qui est l'utilisateur de la requête ? Composé au démarrage (`app.state.authenticator`) :
    l'utilisateur unique en mode `local`, le cookie de session en mode `google`."""

    async def authenticate(self, conn: HTTPConnection) -> CurrentUser:
        """Lève `AppError` 401 `auth_required` si personne n'est connecté."""
        ...


async def get_current_user(conn: HTTPConnection) -> CurrentUser:
    """Utilisateur de la requête ou du WebSocket. Si l'envoyeur du MCP a posé `MCP_IDENTITY` (un
    appel d'outil par un jeton, phase 10), c'est le propriétaire du jeton : même mécanisme quel que
    soit le mode de connexion. Cette variable n'est écrite que par l'envoyeur, jamais lue d'un
    en-tête ni d'un cookie. Sinon, l'authentificateur de l'application (cookie ou utilisateur
    unique)."""
    identity = MCP_IDENTITY.get()
    if identity is not None:
        return CurrentUser(id=identity.user_id, email=None)
    authenticator: Authenticator = conn.app.state.authenticator
    return await authenticator.authenticate(conn)


async def get_interface_user(conn: HTTPConnection) -> CurrentUser:
    """Comme `get_current_user`, mais **réservé à l'interface** : un appel porté par un jeton MCP
    est refusé (403). Pour les routes de gestion de l'accès MCP (jetons, interrupteur,
    confirmations) : un jeton ne se gère jamais lui-même."""
    if MCP_IDENTITY.get() is not None:
        raise AppError("interface_only", "Cette action est réservée à l'interface.", 403)
    authenticator: Authenticator = conn.app.state.authenticator
    return await authenticator.authenticate(conn)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
InterfaceUserDep = Annotated[CurrentUser, Depends(get_interface_user)]


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


def get_publishing(conn: HTTPConnection) -> PublishingProviders:
    """Rendu PDF de nos gabarits (leçons, programme ; D89), ouvert ou injecté au démarrage."""
    publishing: PublishingProviders = conn.app.state.publishing_providers
    return publishing


PublishingDep = Annotated[PublishingProviders, Depends(get_publishing)]

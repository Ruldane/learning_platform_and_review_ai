from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.agents.runtime.handle import AgentRuntime
from app.core.caller import MCP_IDENTITY, require_confirmed_gesture
from app.core.errors import AppError
from app.core.providers import Providers, PublishingProviders
from app.core.security import Cipher
from app.mcp.schema import API_PREFIX, never_reachable
from app.providers.llm.factory import LlmFactory


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Request session: commit at the end of the request, rollback on error."""
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


# `scope="function"`: the code after `yield` (the commit) runs BEFORE the response is sent.
# With the default « request » scope, a commit failure would be reported after a 200 has
# left, and the client could read before the data is committed. Use it everywhere.
Db = Annotated[AsyncSession, Depends(get_db, scope="function")]


# The dependencies below take `HTTPConnection` (the common parent of `Request` and
# `WebSocket`): FastAPI does not inject `Request` on a WebSocket route (phase 1 stream).


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


class Authenticator(Protocol):
    """Who is the request's user? Built at startup (`app.state.authenticator`):
    the single user in `local` mode, the session cookie in `google` mode."""

    async def authenticate(self, conn: HTTPConnection) -> CurrentUser:
        """Raises `AppError` 401 `auth_required` if nobody is signed in."""
        ...


async def get_current_user(conn: HTTPConnection) -> CurrentUser:
    """User of the request or the WebSocket. If the MCP sender set `MCP_IDENTITY` (a tool call
    through a token, phase 10), it is the token's owner: the same mechanism whatever the
    sign-in mode. This variable is only written by the sender, never read from a header
    or a cookie. Otherwise, the application's authenticator (cookie or single user)."""
    identity = MCP_IDENTITY.get()
    if identity is not None:
        if never_reachable(conn.url.path.removeprefix(API_PREFIX), conn.scope.get("method")):
            raise AppError("interface_only", "This action is only available in the app.", 403)
        return CurrentUser(id=identity.user_id, email=None)
    authenticator: Authenticator = conn.app.state.authenticator
    return await authenticator.authenticate(conn)


async def get_interface_user(conn: HTTPConnection) -> CurrentUser:
    """Like `get_current_user`, but **reserved for the interface**: a call carried by an MCP token
    is refused (403). For the routes that manage MCP access (tokens, switch, confirmations):
    a token never manages itself."""
    if MCP_IDENTITY.get() is not None:
        raise AppError("interface_only", "This action is only available in the app.", 403)
    authenticator: Authenticator = conn.app.state.authenticator
    return await authenticator.authenticate(conn)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
InterfaceUserDep = Annotated[CurrentUser, Depends(get_interface_user)]


def get_confirmed_user(user: CurrentUserDep) -> CurrentUser:
    require_confirmed_gesture()
    return user


ConfirmedUserDep = Annotated[CurrentUser, Depends(get_confirmed_user)]


def get_providers(conn: HTTPConnection) -> Providers:
    """External services assembled at startup by `app/bootstrap.py`."""
    providers: Providers = conn.app.state.providers
    return providers


def get_llm_factory(conn: HTTPConnection) -> LlmFactory:
    """Chat model factory (the only place where LLMs are instantiated)."""
    return get_providers(conn).llm_factory


def get_cipher(conn: HTTPConnection) -> Cipher:
    cipher: Cipher = conn.app.state.cipher
    return cipher


def get_runtime(conn: HTTPConnection) -> AgentRuntime:
    """Agent engine (bus, runner) opened by the lifespan (`app.agents.runtime.lifespan`)."""
    runtime: AgentRuntime = conn.app.state.runtime
    return runtime


RuntimeDep = Annotated[AgentRuntime, Depends(get_runtime)]


def get_publishing(conn: HTTPConnection) -> PublishingProviders:
    """PDF rendering of our templates (lessons, program; D89), opened or injected at startup."""
    publishing: PublishingProviders = conn.app.state.publishing_providers
    return publishing


PublishingDep = Annotated[PublishingProviders, Depends(get_publishing)]

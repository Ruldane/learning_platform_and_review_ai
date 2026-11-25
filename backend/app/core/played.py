"""Source chosen when the route is opened (MCP client or forced API provider), restored on
resumes and child sessions of the same account."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

type PlayClient = Literal["claude-code", "codex"]
type ForcedProvider = Literal["anthropic", "glm", "openai"]

PLAY_CLIENTS: tuple[PlayClient, ...] = ("claude-code", "codex")
FORCED_PROVIDERS: tuple[ForcedProvider, ...] = ("anthropic", "glm", "openai")


@dataclass(frozen=True)
class PlayContext:
    """`client`: the route is played by this MCP client; otherwise `provider`: each call goes
    through this API provider; both None: the person's settings."""

    user_id: str
    client: PlayClient | None
    graph: str | None = None
    started: list[str] = field(default_factory=list)
    provider: ForcedProvider | None = None


PLAY_CONTEXT: ContextVar[PlayContext | None] = ContextVar("play_context", default=None)
# Menu choice of the interface for the current request (header `X-Tremplin-Run`, set by
# `RunSourceHeader`): applies to the request's account, under a route already running.
RUN_REQUEST: ContextVar[str | None] = ContextVar("run_request", default=None)
RUN_HEADER = b"x-tremplin-run"


def run_source(user_id: str) -> tuple[PlayClient | None, ForcedProvider | None]:
    """The client and provider of the route in progress for this account, otherwise the menu
    choice of the request, otherwise `(None, None)` (the settings)."""
    play = PLAY_CONTEXT.get()
    if play is not None:
        return (play.client, play.provider) if play.user_id == user_id else (None, None)
    asked = RUN_REQUEST.get()
    return as_client(asked), as_provider(asked)


class RunSourceHeader:
    """ASGI middleware: reads `X-Tremplin-Run` (« claude-code », « codex », « anthropic »,
    « glm », « openai »; any other value means « selon mes réglages »)."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw = dict(scope.get("headers") or []).get(RUN_HEADER, b"").decode("latin-1")
        token = RUN_REQUEST.set(raw.strip() or None)
        try:
            await self.app(scope, receive, send)
        finally:
            RUN_REQUEST.reset(token)


def played_by(user_id: str) -> PlayClient | None:
    return run_source(user_id)[0]


def as_client(value: str | None) -> PlayClient | None:
    return value if value in PLAY_CLIENTS else None


def as_provider(value: str | None) -> ForcedProvider | None:
    return value if value in FORCED_PROVIDERS else None


@contextmanager
def inherit_source(
    user_id: str, client: str | None, provider: str | None, *, has_origin: bool = True
) -> Iterator[None]:
    """Restores the original source, including « Selon mes réglages », before the HTTP choice.
    The context of the active route of the same account keeps priority."""
    playing = PLAY_CONTEXT.get()
    if not has_origin or (playing is not None and playing.user_id == user_id):
        yield
        return
    flag = PLAY_CONTEXT.set(PlayContext(user_id, as_client(client), provider=as_provider(provider)))
    try:
        yield
    finally:
        PLAY_CONTEXT.reset(flag)


@contextmanager
def inherit_play(user_id: str, client: str | None) -> Iterator[None]:
    with inherit_source(user_id, client, None, has_origin=as_client(client) is not None):
        yield

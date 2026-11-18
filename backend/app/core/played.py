"""Source choisie à l'ouverture du parcours (client MCP ou fournisseur d'API forcé), restaurée sur
les reprises et les sessions filles du même compte."""

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
    """`client` : le parcours est joué par ce client MCP ; sinon `provider` : chaque appel passe
    par ce fournisseur d'API ; les deux nuls : les réglages de la personne."""

    user_id: str
    client: PlayClient | None
    graph: str | None = None
    started: list[str] = field(default_factory=list)
    provider: ForcedProvider | None = None


PLAY_CONTEXT: ContextVar[PlayContext | None] = ContextVar("play_context", default=None)
# Choix du menu de l'interface pour la requête en cours (en-tête `X-Tremplin-Run`, posé par
# `RunSourceHeader`) : vaut pour le compte de la requête, sous un parcours déjà en cours.
RUN_REQUEST: ContextVar[str | None] = ContextVar("run_request", default=None)
RUN_HEADER = b"x-tremplin-run"


def run_source(user_id: str) -> tuple[PlayClient | None, ForcedProvider | None]:
    """Le client et le fournisseur du parcours en cours pour ce compte, sinon le choix du menu
    de la requête, sinon `(None, None)` (les réglages)."""
    play = PLAY_CONTEXT.get()
    if play is not None:
        return (play.client, play.provider) if play.user_id == user_id else (None, None)
    asked = RUN_REQUEST.get()
    return as_client(asked), as_provider(asked)


class RunSourceHeader:
    """Middleware ASGI : lit `X-Tremplin-Run` (« claude-code », « codex », « anthropic »,
    « glm », « openai » ; toute autre valeur vaut « selon mes réglages »)."""

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
def inherit_source(user_id: str, client: str | None, provider: str | None) -> Iterator[None]:
    """Rétablit la source d'une session d'origine pour un lancement fait hors de son exécution
    (leçons après validation, correction d'un quiz…). Une source déjà posée l'emporte."""
    known_client, known_provider = as_client(client), as_provider(provider)
    if (known_client is None and known_provider is None) or run_source(user_id) != (None, None):
        yield
        return
    flag = PLAY_CONTEXT.set(PlayContext(user_id, known_client, provider=known_provider))
    try:
        yield
    finally:
        PLAY_CONTEXT.reset(flag)


@contextmanager
def inherit_play(user_id: str, client: str | None) -> Iterator[None]:
    with inherit_source(user_id, client, None):
        yield

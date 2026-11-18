"""Client choisi à l'ouverture du parcours, restauré sur les sessions filles du même compte."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Literal, cast

type PlayClient = Literal["claude-code", "codex"]


@dataclass(frozen=True)
class PlayContext:
    user_id: str
    client: PlayClient
    graph: str | None = None
    started: list[str] = field(default_factory=list)


PLAY_CONTEXT: ContextVar[PlayContext | None] = ContextVar("play_context", default=None)


def played_by(user_id: str) -> PlayClient | None:
    play = PLAY_CONTEXT.get()
    return play.client if play and play.user_id == user_id else None


@contextmanager
def inherit_play(user_id: str, client: str | None) -> Iterator[None]:
    if client not in ("claude-code", "codex") or played_by(user_id) is not None:
        yield
        return
    flag = PLAY_CONTEXT.set(PlayContext(user_id, cast(PlayClient, client)))
    try:
        yield
    finally:
        PLAY_CONTEXT.reset(flag)

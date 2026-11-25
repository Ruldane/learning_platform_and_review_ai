"""The user's inputs during a session (D4, D82): each `user.message` carries a text
and, for the debate, a permanent command (SPEC 3.2: rerun a turn, move on to
proposals, more concrete, shorter). The nodes read them at the next turn."""

from dataclasses import dataclass
from typing import Any, get_args

from app.agents.runtime.events import UserCommand

_COMMANDS: tuple[str, ...] = get_args(UserCommand)


@dataclass(frozen=True)
class UserInput:
    seq: int
    text: str
    command: UserCommand | None


def user_input_of(seq: int, payload: dict[str, Any]) -> UserInput:
    """Input read from a stored payload. A command outside the catalog is ignored (the text
    stays): a node must never fail on a payload written by another version."""
    raw = payload.get("command")
    command: UserCommand | None = raw if raw in _COMMANDS else None
    return UserInput(seq=seq, text=str(payload.get("text") or ""), command=command)

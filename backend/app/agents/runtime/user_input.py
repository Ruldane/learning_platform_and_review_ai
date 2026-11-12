"""Entrées de l'utilisatrice pendant une session (D4, D82) : chaque `user.message` porte un texte
et, pour le débat, une commande permanente (SPEC 3.2 : relancer un tour, passer aux
propositions, plus concret, plus court). Les nœuds les lisent au tour suivant."""

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
    """Entrée lue d'une charge stockée. Une commande hors catalogue est ignorée (le texte
    reste) : un nœud ne doit jamais échouer sur une charge écrite par une autre version."""
    raw = payload.get("command")
    command: UserCommand | None = raw if raw in _COMMANDS else None
    return UserInput(seq=seq, text=str(payload.get("text") or ""), command=command)

"""Qui appelle : l'interface de January ou Claude par le serveur MCP (phase 10, P12).

`MCP_IDENTITY` n'est écrite que par l'envoyeur du MCP (`app/mcp`), jamais depuis un en-tête ni un
cookie : rien d'extérieur ne peut donc la forger. Vide, l'appelant est l'application. Un service
qui écrit (notes de l'IDE, historique des changements) lit `current_caller()` pour savoir qui a
fait le geste : le professeur interne et Claude passent par le même service, seul l'auteur change
(P8)."""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends


@dataclass(frozen=True)
class McpIdentity:
    """L'identité posée par l'envoyeur MCP pour la durée d'un appel : l'utilisatrice propriétaire
    du jeton, le jeton (identifiant, jamais sa valeur), son étiquette, les features qu'il ouvre et
    son mode (`read` par défaut)."""

    user_id: str
    token_id: str
    label: str
    features: frozenset[str]
    mode: Literal["read", "write"]


MCP_IDENTITY: ContextVar[McpIdentity | None] = ContextVar("mcp_identity", default=None)


@dataclass(frozen=True)
class Caller:
    """`kind` : `app` (l'interface, ou une tâche interne) ou `mcp` ; `label` : « app » ou
    l'étiquette du jeton."""

    kind: Literal["app", "mcp"]
    label: str


def current_caller() -> Caller:
    """`app` si `MCP_IDENTITY` est vide, sinon l'étiquette du jeton."""
    identity = MCP_IDENTITY.get()
    if identity is None:
        return Caller(kind="app", label="app")
    return Caller(kind="mcp", label=identity.label)


CallerDep = Annotated[Caller, Depends(current_caller)]

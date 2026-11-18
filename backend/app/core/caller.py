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

from app.core.errors import AppError


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


def january_only() -> None:
    """Dépendance de route : un geste de January (ses réponses à un quiz, la note d'une fiche, le
    rendu d'un projet) n'est jamais fait à sa place par Claude. Sous une identité MCP : 403
    `mcp_gesture_forbidden`, avant toute écriture. La déclaration MCP de ces routes les exclut déjà
    (défense en profondeur : un registre mal déclaré n'ouvre pas le geste)."""
    if MCP_IDENTITY.get() is not None:
        raise AppError(
            "mcp_gesture_forbidden",
            "Ce geste est réservé à January dans l'interface : ses réponses et son rendu ne se "
            "font jamais à sa place.",
            403,
        )


JanuaryOnly = Depends(january_only)

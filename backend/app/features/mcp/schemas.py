"""Schémas de l'accès MCP (phase 10, P1, P15 à P19) : définitifs dès 10.P. Un jeton n'apparaît en
clair qu'une fois, dans `McpTokenCreated` ; ni liste ni journal ne le rendent jamais."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.mcp import ConfirmationStatus, McpMode

__all__ = [
    "McpActionOut",
    "McpCallOut",
    "McpChangeOut",
    "McpConfirmationOut",
    "ConfirmationStatus",
    "McpFeatureOut",
    "McpMode",
    "McpRequestField",
    "McpRequestPreview",
    "McpSettingsIn",
    "McpSettingsOut",
    "McpTokenCreateIn",
    "McpTokenCreated",
    "McpTokenOut",
    "McpUndoOut",
]

LABEL_MAX = 60
ExpiryDays = Literal[1, 7, 30, 90]
ActionKind = Literal["route", "graph"]


class McpSettingsIn(BaseModel):
    """L'interrupteur général : faux = aucun jeton n'ouvre rien (coupé par défaut)."""

    enabled: bool


class McpSettingsOut(McpSettingsIn):
    pass


class McpFeatureOut(BaseModel):
    """Une feature qui déclare des outils MCP : son nom et ses outils par niveau."""

    feature: str
    read_actions: int
    write_actions: int
    confirm_actions: int


class McpActionOut(BaseModel):
    """Un outil exposé (table des niveaux). `kind` : une route ou un graphe de l'application.
    `untrusted` : les champs rendus comme données, jamais comme consignes."""

    name: str
    feature: str
    kind: ActionKind
    route: str | None
    level: Literal[1, 2, 3]
    summary: str | None
    side_effects: Literal["db", "external"]
    untrusted: list[str]


# « Tout cocher » ouvre toutes les features (75 au 23/11) ; marge pour les suivantes (D306).
MAX_TOKEN_FEATURES = 120


class McpTokenCreateIn(BaseModel):
    """Crée un jeton : limité à certaines features, lecture seule par défaut, 30 jours par
    défaut (1, 7, 30 ou 90)."""

    label: str = Field(min_length=1, max_length=LABEL_MAX)
    features: list[str] = Field(min_length=1, max_length=MAX_TOKEN_FEATURES)
    mode: McpMode = "read"
    expires_in_days: ExpiryDays = 30


class McpTokenOut(BaseModel):
    """Un jeton, sans sa valeur : on ne la revoit jamais."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    features: list[str]
    mode: McpMode
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class McpTokenCreated(McpTokenOut):
    """La réponse à la création : `token` (`tmcp_…`) n'est montré qu'ici, une seule fois."""

    token: str


class McpRequestField(BaseModel):
    """Un champ de la requête à confirmer : son nom et sa valeur en texte (objets et listes en JSON
    compact), tronquée à 500 caractères ; les clés d'API sont masquées."""

    name: str
    value_preview: str


class McpRequestPreview(BaseModel):
    """La requête qui partira à la confirmation, de quoi la lire en entier : méthode, route (le
    gabarit, sans identifiant), libellé lisible de la cible quand la route en a une (titre, nom ;
    lu par la route de lecture de la même ressource ; un texte venu du web est entouré de
    `<donnee_non_fiable>`), **tous** les champs du corps et des paramètres, et `truncated` si une
    valeur ou le total (4 000 caractères) a été coupé."""

    method: str
    route: str
    target_label: str | None
    fields: list[McpRequestField]
    truncated: bool


class McpConfirmationOut(BaseModel):
    """Une demande « À confirmer » (niveau 3) : ce que Claude veut faire (un résumé neutre et la
    requête complète en `request`) et le verdict d'un éventuel contrôle préalable. Rien ne
    s'exécute avant la confirmation."""

    id: str
    token_id: str
    action: str
    summary: str
    request: McpRequestPreview
    precheck: dict[str, Any] | None
    status: ConfirmationStatus
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime


class McpCallOut(BaseModel):
    """Une ligne du journal : l'outil, le niveau, le code de résultat, la durée, les identifiants.
    Jamais le contenu. Niveau 0 : appel refusé avant la résolution de l'outil ; `token_id` vide :
    jeton non reconnu."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    token_id: str | None
    action: str
    level: Literal[0, 1, 2, 3]
    code: int
    duration_ms: int
    ids: dict[str, Any]
    created_at: datetime


class McpChangeOut(BaseModel):
    """Les changements d'un appel de niveau 2 : de quoi les annuler ensemble (`undone_at` posé
    une fois annulés)."""

    call_id: str
    action: str
    rows: int
    tables: list[str]
    undone_at: datetime | None
    created_at: datetime


class McpUndoOut(BaseModel):
    """`undone` : le nombre de lignes remises dans leur état d'avant."""

    call_id: str
    undone: int

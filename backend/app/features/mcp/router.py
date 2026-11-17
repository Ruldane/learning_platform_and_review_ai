"""API de gestion de l'accès MCP (phase 10, P1, P15 à P19) : interrupteur général, tables des
features et des outils, jetons, demandes « À confirmer », journal des appels, changements et
annulation. Posée par 10.P (surface et schémas définitifs) : chaque route répond 501
`not_implemented` jusqu'à ce que 10.B1 (interrupteur, jetons, journal) et 10.B2 (outils,
confirmations, changements) la remplissent. Ces routes sont **de l'interface** : la feature `mcp`
n'est jamais exposée au MCP (niveau 4), et un jeton MCP n'ouvre jamais `/api/v1`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.core.deps import get_current_user
from app.core.field_paths import FieldPathsRoute
from app.core.stubs import not_implemented
from app.features.mcp.schemas import (
    McpActionOut,
    McpCallOut,
    McpChangeOut,
    McpConfirmationOut,
    McpFeatureOut,
    McpSettingsIn,
    McpSettingsOut,
    McpTokenCreated,
    McpTokenCreateIn,
    McpTokenOut,
    McpUndoOut,
)

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(get_current_user)],
)

Id = Annotated[str, Path(min_length=1, max_length=36)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/settings", response_model=McpSettingsOut)
async def get_settings() -> McpSettingsOut:
    """L'interrupteur général du MCP (coupé par défaut)."""
    not_implemented()


@router.put("/settings", response_model=McpSettingsOut)
async def put_settings(body: McpSettingsIn) -> McpSettingsOut:
    """Allume ou coupe tout l'accès MCP d'un geste."""
    not_implemented()


@router.get("/features", response_model=list[McpFeatureOut])
async def list_features() -> list[McpFeatureOut]:
    """Les features qui déclarent des outils, avec le nombre d'outils par niveau."""
    not_implemented()


@router.get("/actions", response_model=list[McpActionOut])
async def list_actions() -> list[McpActionOut]:
    """La table des outils exposés et de leur niveau."""
    not_implemented()


@router.post("/tokens", response_model=McpTokenCreated, status_code=201)
async def create_token(body: McpTokenCreateIn) -> McpTokenCreated:
    """Crée un jeton ; sa valeur n'est rendue qu'ici, une seule fois."""
    not_implemented()


@router.get("/tokens", response_model=list[McpTokenOut])
async def list_tokens() -> list[McpTokenOut]:
    """Mes jetons (sans leur valeur), révoqués compris."""
    not_implemented()


@router.delete("/tokens/{token_id}", status_code=204, response_class=Response)
async def revoke_token(token_id: Id) -> Response:
    """Révoque un jeton : il cesse de fonctionner aussitôt."""
    not_implemented()


@router.get("/confirmations", response_model=list[McpConfirmationOut])
async def list_confirmations() -> list[McpConfirmationOut]:
    """Les demandes « À confirmer », les plus récentes d'abord."""
    not_implemented()


@router.post("/confirmations/{confirmation_id}/confirm", response_model=McpConfirmationOut)
async def confirm(confirmation_id: Id) -> McpConfirmationOut:
    """Exécute la demande, une seule fois ; expirée, refusée ou déjà traitée : 409."""
    not_implemented()


@router.post("/confirmations/{confirmation_id}/refuse", response_model=McpConfirmationOut)
async def refuse(confirmation_id: Id) -> McpConfirmationOut:
    """Refuse la demande : elle ne s'exécutera jamais."""
    not_implemented()


@router.get("/calls", response_model=list[McpCallOut])
async def list_calls(limit: Limit = 50) -> list[McpCallOut]:
    """Le journal des appels MCP (outil, niveau, code, durée), jamais leur contenu."""
    not_implemented()


@router.get("/changes", response_model=list[McpChangeOut])
async def list_changes(limit: Limit = 50) -> list[McpChangeOut]:
    """Les changements faits par Claude (niveau 2), annulables un appel à la fois."""
    not_implemented()


@router.post("/changes/{call_id}/undo", response_model=McpUndoOut)
async def undo_changes(call_id: Id) -> McpUndoOut:
    """Remet les lignes d'un appel dans leur état d'avant, si aucune n'a changé depuis (409
    sinon)."""
    not_implemented()

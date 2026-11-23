"""« Tout cocher » ouvre toutes les features au jeton : la borne du schéma doit les contenir
toutes, avec de la marge pour les features à venir (D306)."""

import pytest
from pydantic import ValidationError

from app.features.mcp.schemas import MAX_TOKEN_FEATURES, McpTokenCreateIn
from app.features.registry import MCP_FEATURES


def test_cap_holds_every_declared_feature() -> None:
    assert len(MCP_FEATURES) <= MAX_TOKEN_FEATURES


def test_select_all_payload_is_accepted() -> None:
    names = [f"feature_{n}" for n in range(MAX_TOKEN_FEATURES)]
    assert len(McpTokenCreateIn(label="Tout", features=names).features) == MAX_TOKEN_FEATURES


def test_above_cap_is_refused() -> None:
    names = [f"feature_{n}" for n in range(MAX_TOKEN_FEATURES + 1)]
    with pytest.raises(ValidationError):
        McpTokenCreateIn(label="Trop", features=names)

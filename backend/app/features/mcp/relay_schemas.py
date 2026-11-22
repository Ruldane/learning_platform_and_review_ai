"""Contrats d'appairage du relais, indépendants des jetons de l'interface."""

from typing import Literal

from pydantic import BaseModel, Field

RelayState = Literal[
    "unpaired", "pending", "paired", "incomplete", "expired", "revoked", "disabled"
]


class RelayCode(BaseModel):
    code: str = Field(pattern=r"^trp_[A-Za-z0-9_-]{43}$")


class RelayToken(BaseModel):
    token: str


class RelayStatus(BaseModel):
    state: RelayState
    missing_features: list[str] = Field(default_factory=list)

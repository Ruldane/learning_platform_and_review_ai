from typing import Literal

from pydantic import BaseModel


class MeOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    auth_mode: str


class ClaimIn(BaseModel):
    """Le choix de la toute première connexion Google : reprendre l'espace local (même `id`,
    donc aucune donnée déplacée) ou repartir d'un espace vide (l'espace local reste intact)."""

    choice: Literal["take_local", "fresh"]

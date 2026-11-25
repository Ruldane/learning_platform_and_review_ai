from typing import Literal

from pydantic import BaseModel


class MeOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    auth_mode: str


class ClaimIn(BaseModel):
    """The choice of the very first Google sign-in: take over the local space (same `id`, so no
    data moved) or start from an empty space (the local space stays intact)."""

    choice: Literal["take_local", "fresh"]

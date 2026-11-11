"""Types de la fabrique LLM. L'interface (protocoles, fabrique) est complétée en tâche 0.7."""

from typing import Literal

from pydantic import BaseModel

Tier = Literal["rapide", "standard", "fort", "vision"]
TIERS: tuple[Tier, ...] = ("rapide", "standard", "fort", "vision")


class ModelChoice(BaseModel):
    """Fournisseur et identifiant de modèle retenus pour un niveau ou un agent."""

    provider: str
    model: str

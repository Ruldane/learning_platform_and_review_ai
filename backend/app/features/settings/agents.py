"""Le catalogue des agents dont le modèle se surcharge (mode avancé, P17) : le registre `AGENTS`,
sans les agents de démonstration, dans l'ordre du registre."""

from app.agents.registry import AGENTS
from app.features.settings.schemas import AgentOut

DEMO_PREFIX = "demo_"


def agent_catalogue() -> list[AgentOut]:
    """Nom et niveau de chaque agent de `AGENTS` hors `demo_*`, dans l'ordre du registre (celui
    des équipes d'agents : le front l'affiche tel quel)."""
    return [
        AgentOut(name=spec.name, tier=spec.tier)
        for spec in AGENTS.values()
        if not spec.name.startswith(DEMO_PREFIX)
    ]

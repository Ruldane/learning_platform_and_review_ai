"""The catalog of agents whose model can be overridden (advanced mode, P17): the `AGENTS`
registry, without the demo agents, in registry order."""

from app.agents.registry import AGENTS
from app.features.settings.schemas import AgentOut, is_overridable


def agent_catalogue() -> list[AgentOut]:
    """Name and tier of each agent in `AGENTS` except `demo_*`, in registry order (that of the
    agent teams: the front shows it as is)."""
    return [
        AgentOut(name=spec.name, tier=spec.tier)
        for spec in AGENTS.values()
        if is_overridable(spec.name)
    ]

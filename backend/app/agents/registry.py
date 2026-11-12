"""Registre des agents : un nom (slug, identique côté front dans `agentColors.ts`) et un niveau
de modèle. Le prompt de chaque agent est le fichier `prompts/<nom>.md`. Rempli par les graphes."""

from dataclasses import dataclass

from app.core.errors import AppError
from app.providers.llm.base import Tier


@dataclass(frozen=True)
class AgentSpec:
    name: str
    tier: Tier


AGENTS: dict[str, AgentSpec] = {
    spec.name: spec
    for spec in (
        AgentSpec(name="demo_proponent", tier="rapide"),  # Défenseur du graphe `demo_debate`
        AgentSpec(name="demo_critic", tier="rapide"),  # Critique du graphe `demo_debate`
        AgentSpec(name="archivist", tier="rapide"),  # Archiviste du graphe `learned_document`
        AgentSpec(name="scout", tier="rapide"),  # Éclaireur (`web_research`, Conseil)
        AgentSpec(name="moderator", tier="rapide"),  # Modérateur du Conseil
        AgentSpec(name="strategist", tier="fort"),  # Stratège : débat, propositions, programme
        AgentSpec(name="practitioner", tier="standard"),  # Praticien : voix du terrain
        AgentSpec(name="skeptic", tier="standard"),  # Sceptique : objections, faisabilité
        AgentSpec(name="scribe", tier="rapide"),  # Scribe : tableau et compte rendu
        AgentSpec(name="writer", tier="fort"),  # Rédacteur : la leçon d'un module
        AgentSpec(name="verifier", tier="standard"),  # Vérificateur : structure, faits, liens
    )
}


def get_agent(name: str) -> AgentSpec:
    spec = AGENTS.get(name)
    if spec is None:
        raise AppError("unknown_agent", f"Agent inconnu : {name}", 404, {"agent": name})
    return spec

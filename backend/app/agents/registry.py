"""Registre des agents : un nom (slug, identique côté front dans `agentColors.ts`) et un niveau
de modèle. Le prompt de chaque agent est le fichier `prompts/<nom>.md`. Rempli par les graphes."""

from dataclasses import dataclass

from app.agents.tools.conversation_port import BRAIN_LIBRARIAN, LESSON_PROFESSOR, TRAINING_TUTOR
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
        AgentSpec(name="examiner", tier="standard"),  # Examinateur : quiz d'un module, notes
        AgentSpec(name="tutor", tier="standard"),  # Tuteur : sessions d'étude guidées
        AgentSpec(name="analyst", tier="rapide"),  # Analyste : analyse d'une offre, écart
        AgentSpec(name="designer", tier="vision"),  # Maquettiste : design d'un CV (images)
        AgentSpec(name="ats_reader", tier="standard"),  # Lecteur ATS : revue du CV (mots clés)
        AgentSpec(name="recruiter", tier="standard"),  # Recruteur : revue du CV (impact)
        AgentSpec(name="tracker", tier="rapide"),  # Assistant de suivi : fiche en une phrase
        AgentSpec(name="interviewer", tier="fort"),  # Intervieweur : entretien blanc, débrief
        AgentSpec(name="manager", tier="standard"),  # Manager du poste : comité de recrutement
        AgentSpec(name="colleague", tier="standard"),  # Futur collègue : comité de recrutement
        # Professeur de l'IDE : rapide (indices, annotations), `fort` choisi par le nœud pour les
        # explications et les propositions ; rédacteur d'exercices : standard
        AgentSpec(name="professor", tier="rapide"),
        AgentSpec(name=LESSON_PROFESSOR, tier="rapide"),
        AgentSpec(name=TRAINING_TUTOR, tier="rapide"),
        AgentSpec(name=BRAIN_LIBRARIAN, tier="rapide"),
        AgentSpec(name="exercise_writer", tier="standard"),
        AgentSpec(name="podcast_host", tier="standard"),
    )
}


def get_agent(name: str) -> AgentSpec:
    spec = AGENTS.get(name)
    if spec is None:
        raise AppError("unknown_agent", f"Agent inconnu : {name}", 404, {"agent": name})
    return spec

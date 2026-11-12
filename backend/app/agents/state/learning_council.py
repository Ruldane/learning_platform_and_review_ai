"""État du parcours `learning_council` (D84). Il hérite de l'état de l'Éclaireur : ses nœuds
entrent dans le Conseil tels quels, nœud pour nœud (mêmes clés, mêmes points de contrôle que
`web_research`), sans sous-graphe."""

import operator
from typing import Annotated, Any

from app.agents.state.web_research import WebResearchState


class CouncilState(WebResearchState, total=False):
    goal_id: str
    goal: dict[str, Any]  # `GoalBrief` en JSON (échéance en ISO)
    context: str  # contexte mémoire du Modérateur, déjà encadré par le port
    framing_questions: list[dict[str, str]]  # {id, question}, ids `q1`… imposés par le code
    framing_answers: dict[str, str]  # réponses de January, par id de question
    people: list[dict[str, Any]]  # praticiens gardés : {source_id, name, role, url, where}
    # Débat (D85)
    catalog: list[
        dict[str, Any]
    ]  # {index, title, summary, url, memory_item_id}, numéroté au tour 1
    round: int  # tour en cours (1 : positions)
    rounds_target: int  # dernier tour prévu : 1 + `debate_rounds`, 8 au plus
    order: list[str]  # ordre de parole du tour, fixé par le Modérateur
    turn_index: int  # prochain orateur dans `order`
    turns: Annotated[list[dict[str, Any]], operator.add]  # {round, agent, text}
    last_input_seq: int  # dernier `user.message` lu
    notes: Annotated[list[str], operator.add]  # tous les messages de January lus
    round_notes: list[str]  # messages de January à traiter au tour en cours
    angle: str | None  # `more_concrete` ou `shorter`, pour le tour en cours
    stop: bool  # fin du débat demandée (January ou Modérateur)
    board_step: int  # dernier numéro d'étape du tableau utilisé
    minutes: str  # compte rendu du Scribe
    # Propositions et choix (D85)
    batch: int
    proposals: list[dict[str, Any]]  # lot en cours : {proposal_id, rank, name, …ProposalDraft}
    choice: dict[str, Any] | None  # `ChoiceAnswer` en JSON ; None : réponse invalide
    summary: str

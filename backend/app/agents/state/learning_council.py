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
    catalog: list[dict[str, Any]]  # sources et éléments de mémoire citables (4.4)
    round: int
    rounds_target: int
    order: list[str]
    turn_index: int
    turns: Annotated[list[dict[str, Any]], operator.add]
    last_input_seq: int
    notes: Annotated[list[str], operator.add]
    angle: str | None
    stop: bool
    batch: int
    proposals: list[dict[str, Any]]
    choice: dict[str, Any] | None
    summary: str

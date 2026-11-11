"""État du parcours `demo_debate` : un débat à deux agents, interrompu pour l'utilisatrice."""

import operator
from typing import Annotated, Protocol, TypedDict


class DemoDebateState(TypedDict, total=False):
    topic: str
    round: int  # tours terminés (le Critique l'incrémente)
    turns: Annotated[list[dict[str, str]], operator.add]  # {"agent": nom, "texte": réplique}
    last_message_seq: int  # `seq` du dernier `user.message` déjà lu par un agent
    user_notes: Annotated[list[str], operator.add]  # messages de l'utilisatrice, dans l'ordre
    user_choice: str | None  # dernière réponse à la question d'angle
    summary: str


class DebateNode(Protocol):
    """Forme d'un nœud (paramètre nommé `state`, comme l'attend `StateGraph.add_node`)."""

    async def __call__(self, state: DemoDebateState) -> DemoDebateState: ...

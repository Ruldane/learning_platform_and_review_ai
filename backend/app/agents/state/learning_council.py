"""State of the `learning_council` graph (D84). It inherits the Scout's state: its nodes
join the Council as they are, node for node (same keys, same checkpoints as
`web_research`), without a subgraph."""

import operator
from typing import Annotated, Any

from app.agents.state.web_research import WebResearchState


class CouncilState(WebResearchState, total=False):
    goal_id: str
    goal: dict[str, Any]  # `GoalBrief` as JSON (deadline in ISO)
    context: str  # Moderator's memory context, already framed by the port
    framing_questions: list[dict[str, str]]  # {id, question}, ids `q1`... set by the code
    framing_answers: dict[str, str]  # January's answers, by question id
    people: list[dict[str, Any]]  # practitioners kept: {source_id, name, role, url, where}
    # Debate (D85)
    catalog: list[
        dict[str, Any]
    ]  # {index, title, summary, url, memory_item_id}, numbered in round 1
    round: int  # current round (1: positions)
    rounds_target: int  # last planned round: 1 + `debate_rounds`, 8 at most
    order: list[str]  # speaking order of the round, set by the Moderator
    turn_index: int  # next speaker in `order`
    turns: Annotated[list[dict[str, Any]], operator.add]  # {round, agent, text}
    last_input_seq: int  # dernier `user.message` lu
    notes: Annotated[list[str], operator.add]  # all of January's messages read
    round_notes: list[str]  # January's messages to handle in the current round
    angle: str | None  # `more_concrete` or `shorter`, for the current round
    stop: bool  # end of debate requested (January or Moderator)
    board_step: int  # last step number of the board used
    minutes: str  # Scribe's minutes
    # Proposals and choice (D85)
    batch: int
    proposals: list[dict[str, Any]]  # current batch: {proposal_id, rank, name, …ProposalDraft}
    choice: dict[str, Any] | None  # `ChoiceAnswer` as JSON; None: invalid answer
    summary: str

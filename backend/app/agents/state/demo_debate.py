"""State of the `demo_debate` graph: a two-agent debate, interrupted for the user."""

import operator
from typing import Annotated, Protocol, TypedDict


class DemoDebateState(TypedDict, total=False):
    topic: str
    round: int  # completed turns (the Critic increments it)
    turns: Annotated[list[dict[str, str]], operator.add]  # {"agent": name, "text": line}
    last_message_seq: int  # `seq` of the last `user.message` already read by an agent
    user_notes: Annotated[list[str], operator.add]  # the user's messages, in order
    user_choice: str | None  # last answer to the angle question
    summary: str


class DebateNode(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: DemoDebateState) -> DemoDebateState: ...

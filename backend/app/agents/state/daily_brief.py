"""State of the `daily_brief` graph (D161). What is stored (resource, advice) is in the database,
behind the `BriefStore` port: each node rereads `context` and skips its section if it is already
stored (SPEC 9.4). The state keeps only the brief's id and the `run.completed` summary:
neither subject, nor fact, nor text (never user data in a checkpoint)."""

from typing import Protocol, TypedDict


class DailyBriefState(TypedDict, total=False):
    brief_id: str
    summary: str  # `run.completed` summary


class Node(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: DailyBriefState) -> DailyBriefState: ...

"""State of the `project_brief` graph (D165). The module's inputs are in the database, behind the
`ProjectStore` port: each node rereads them. The state keeps only the project id, the written brief
(for the time it takes to go from the `write` node to the `save` node, like the proposals of a CV
review: project data in checkpoints, never in a log) and the summary of
`run.completed`."""

from typing import Any, Protocol, TypedDict


class ProjectBriefState(TypedDict, total=False):
    project_id: str
    brief: dict[str, Any]  # `ProjectBrief` as JSON
    summary: str  # `run.completed` summary


class Node(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: ProjectBriefState) -> ProjectBriefState: ...

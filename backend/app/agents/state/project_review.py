"""State of the `project_review` graph (D165). The brief, submission and profile live in the
database, behind the `ProjectStore` port: each node rereads them. The state keeps what passes
between nodes: the repo text (read once, for the session), the evaluation and the drafts, as JSON.
Project data in the checkpoints, never in a log."""

from typing import Any, Literal, Protocol, TypedDict


class ProjectReviewState(TypedDict, total=False):
    project_id: str
    mode: Literal["review", "drafts"]  # `drafts`: only the drafts of a validated project
    title: str  # title of the brief, for `artifact.ready`
    repo_text: str | None  # the README read, cut at 8,000 characters
    repo_status: Literal["read", "unreadable", "none"]
    nothing_to_read: bool  # neither description nor readable repository: no evaluation
    first_drafts: dict[str, Any]  # `ProjectDrafts` of the first try, reread by the retry
    retry_needed: bool  # a draft has terms or a length out of bounds
    outcome: dict[str, Any]  # `ReviewOutcome` as JSON (without drafts before `drafts`)
    drafts_saved: bool  # `drafts` mode: the port stored the drafts (false: write ignored)
    summary: str  # `run.completed` summary


class Node(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: ProjectReviewState) -> ProjectReviewState: ...

"""State of the `ide_teacher` graph (10.A3). The session, files and notes live in the database (port
`IdeStore`): the state keeps only the `run.completed` summary."""

from typing import Protocol, TypedDict


class IdeTeacherState(TypedDict, total=False):
    ide_session_id: str
    trigger: str
    question: str | None
    file_path: str | None
    line: int | None
    run_id: str | None
    error_key: str | None
    level: int | None
    summary: str


class Node(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: IdeTeacherState) -> IdeTeacherState: ...

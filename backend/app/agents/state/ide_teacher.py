"""État du parcours `ide_teacher` (10.A3). La séance, les fichiers et les notes sont en base (port
`IdeStore`) : l'état ne garde que le résumé de `run.completed`."""

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
    """Forme d'un nœud (paramètre nommé `state`, comme l'attend `StateGraph.add_node`)."""

    async def __call__(self, state: IdeTeacherState) -> IdeTeacherState: ...

"""State of the `ide_exercise` graph (10.A3): only the `run.completed` summary (the draft,
the stored exercise and its passing tests go through the `IdeStore` port)."""

from typing import Protocol, TypedDict


class IdeExerciseState(TypedDict, total=False):
    topic: str
    level: str
    summary: str


class Node(Protocol):
    async def __call__(self, state: IdeExerciseState) -> IdeExerciseState: ...

"""État du parcours `ide_exercise` (10.A3) : seulement le résumé de `run.completed` (le brouillon,
l'exercice rangé et ses tests passent par le port `IdeStore`)."""

from typing import Protocol, TypedDict


class IdeExerciseState(TypedDict, total=False):
    topic: str
    level: str
    summary: str


class Node(Protocol):
    async def __call__(self, state: IdeExerciseState) -> IdeExerciseState: ...

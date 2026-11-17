"""Parcours `ide_exercise` (10.A3) : le rédacteur d'exercices écrit un exercice sur un sujet, le
bac à sable en vérifie la solution, l'exercice est rangé.

START -> write -> END

Aucune interruption. Lancé seulement par `POST /ide/exercises/generate` (`ROUTE_ONLY`)."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.exercise_writer import make_write
from app.agents.runtime.deps import GraphDeps
from app.agents.state.ide_exercise import IdeExerciseState

__all__ = ["IdeExerciseInput", "build"]


class IdeExerciseInput(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(IdeExerciseState)
    graph.add_node("write", make_write(deps))
    graph.add_edge(START, "write")
    graph.add_edge("write", END)
    return graph

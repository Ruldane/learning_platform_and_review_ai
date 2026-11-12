"""Parcours `quiz` (SPEC F9, 9.2, D100) : un seul parcours à deux modes. `generate` : l'Examinateur
écrit le quiz d'un module et ses fiches de révision ; `grade` : il note les réponses ouvertes
d'une tentative (les QCM sont notés par le code). Aucune interruption.

START -> route_mode
generate : material -> write -> route_write
           route_write : quiz conforme -> save_quiz -> END ;
                         invalide après deux re-demandes -> failed -> END (`quiz_failed`)
grade :    load_attempt -> grade_open -> save_grades -> announce -> END
"""

from typing import Any, Literal, Self

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from app.agents.nodes.examiner import make_grade_open, make_write, route_write
from app.agents.nodes.examiner_flow import (
    make_announce,
    make_failed,
    make_load_attempt,
    make_material,
    make_save_grades,
    make_save_quiz,
    route_mode,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.quiz import QuizState


class QuizInput(BaseModel):
    mode: Literal["generate", "grade"]
    quiz_id: str | None = Field(default=None, min_length=36, max_length=36)
    attempt_id: str | None = Field(default=None, min_length=36, max_length=36)

    @model_validator(mode="after")
    def _id_of_mode(self) -> Self:
        """`generate` demande le quiz, `grade` la tentative (422 `invalid_input` sinon)."""
        if self.mode == "generate" and self.quiz_id is None:
            raise ValueError("Écrire un quiz demande `quiz_id`.")
        if self.mode == "grade" and self.attempt_id is None:
            raise ValueError("Noter une tentative demande `attempt_id`.")
        return self


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(QuizState)
    graph.add_node("material", make_material(deps))
    graph.add_node("write", make_write(deps))
    graph.add_node("save_quiz", make_save_quiz(deps))
    graph.add_node("failed", make_failed(deps))
    graph.add_node("load_attempt", make_load_attempt(deps))
    graph.add_node("grade_open", make_grade_open(deps))
    graph.add_node("save_grades", make_save_grades(deps))
    graph.add_node("announce", make_announce(deps))
    graph.add_conditional_edges(START, route_mode, ["material", "load_attempt"])
    for source, target in [
        ("material", "write"),
        ("save_quiz", END),
        ("failed", END),
        ("load_attempt", "grade_open"),
        ("grade_open", "save_grades"),
        ("save_grades", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("write", route_write, ["save_quiz", "failed"])
    return graph

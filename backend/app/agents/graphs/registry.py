"""Registre des parcours (graphes d'agents). Un parcours se déclare ici et nulle part ailleurs :
`POST /sessions` valide l'entrée avec `input_model`, le runner compile `build(deps)`."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langgraph.graph import StateGraph
from pydantic import BaseModel

from app.agents.graphs import (
    demo_debate,
    learned_document,
    learning_council,
    lesson_factory,
    program_builder,
    web_research,
)
from app.agents.runtime.deps import GraphDeps
from app.core.errors import AppError


@dataclass(frozen=True)
class GraphSpec:
    name: str
    input_model: type[BaseModel]  # `model_dump()` = état initial
    build: Callable[
        [GraphDeps], StateGraph[Any, Any, Any, Any]
    ]  # non compilé : le runner s'en charge


GRAPHS: dict[str, GraphSpec] = {
    spec.name: spec
    for spec in (
        GraphSpec("demo_debate", demo_debate.DemoDebateInput, demo_debate.build),
        GraphSpec(
            "learned_document", learned_document.LearnedDocumentInput, learned_document.build
        ),
        GraphSpec("web_research", web_research.WebResearchInput, web_research.build),
        GraphSpec(
            "learning_council", learning_council.LearningCouncilInput, learning_council.build
        ),
        GraphSpec("program_builder", program_builder.ProgramBuilderInput, program_builder.build),
        GraphSpec("lesson_factory", lesson_factory.LessonFactoryInput, lesson_factory.build),
    )
}


def get_graph(name: str) -> GraphSpec:
    spec = GRAPHS.get(name)
    if spec is None:
        raise AppError("unknown_graph", f"Parcours inconnu : {name}", 404, {"graph": name})
    return spec

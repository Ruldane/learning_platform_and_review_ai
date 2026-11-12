"""Parcours `lesson_factory` (SPEC 3.5, 3.6, D90) : pour un module d'un programme validé,
l'Éclaireur cherche et note des sources (nœuds de `web_research`, tels quels), choisit 3 à 6
ressources, le Rédacteur écrit la leçon, le Vérificateur la contrôle (deux révisions au plus) ;
elle est publiée ou marquée en échec, puis la chaîne passe au module suivant. Aucune
interruption.

START -> brief -> plan -> search -> read -> judge -> remember -> pick_resources
pick_resources : aucune source retenue -> fail_lesson ; sinon -> write
write -> verify -> route_verify
route_verify : conforme -> publish ; problèmes et révisions < 2 -> write ; sinon -> fail_lesson
publish / fail_lesson -> next -> END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.lesson_flow import (
    make_brief,
    make_fail_lesson,
    make_next,
    make_publish,
    route_resources,
)
from app.agents.nodes.scout import make_judge, make_plan, make_read, make_remember, make_search
from app.agents.nodes.scout.resources import make_pick_resources
from app.agents.nodes.verifier import make_verify, route_verify
from app.agents.nodes.writer import make_write
from app.agents.runtime.deps import GraphDeps
from app.agents.state.lesson_factory import LessonFactoryState


class LessonFactoryInput(BaseModel):
    program_id: str = Field(min_length=36, max_length=36)
    module_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(LessonFactoryState)
    graph.add_node("brief", make_brief(deps))
    graph.add_node("plan", make_plan(deps))
    graph.add_node("search", make_search(deps))
    graph.add_node("read", make_read(deps))
    graph.add_node("judge", make_judge(deps))
    graph.add_node("remember", make_remember(deps))
    graph.add_node("pick_resources", make_pick_resources(deps))
    graph.add_node("write", make_write(deps))
    graph.add_node("verify", make_verify(deps))
    graph.add_node("publish", make_publish(deps))
    graph.add_node("fail_lesson", make_fail_lesson(deps))
    graph.add_node("next", make_next(deps))
    for source, target in [
        (START, "brief"),
        ("brief", "plan"),
        ("plan", "search"),
        ("search", "read"),
        ("read", "judge"),
        ("judge", "remember"),
        ("remember", "pick_resources"),
        ("write", "verify"),
        ("publish", "next"),
        ("fail_lesson", "next"),
        ("next", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("pick_resources", route_resources, ["write", "fail_lesson"])
    graph.add_conditional_edges("verify", route_verify, ["publish", "write", "fail_lesson"])
    return graph

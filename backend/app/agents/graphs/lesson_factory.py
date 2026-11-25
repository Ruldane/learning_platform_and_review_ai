"""Graph `lesson_factory` (SPEC 3.5, 3.6, D90): for a module of a validated program,
the Scout searches and notes sources (`web_research` nodes, as they are), picks 3 to 6
resources, the Writer writes the lesson, the Verifier checks it (two revisions at most);
it is published or marked as failed, then the chain moves to the next module. A direct
submission provides the first draft and only verifies its module.

START -> brief -> plan -> search -> read -> judge -> remember -> pick_resources
pick_resources: no source kept -> fail_lesson; draft submitted -> verify; otherwise -> write
write -> verify -> route_verify
route_verify: compliant -> publish; problems and revisions < 2 -> write; otherwise -> fail_lesson
publish / fail_lesson -> next -> END (soumission directe -> END)
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.lesson_flow import (
    make_brief,
    make_fail_lesson,
    make_next,
    make_publish,
    route_next,
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
    verification: bool = False


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
        ("next", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges(
        "pick_resources", route_resources, ["write", "verify", "fail_lesson"]
    )
    graph.add_conditional_edges("verify", route_verify, ["publish", "write", "fail_lesson"])
    graph.add_conditional_edges("publish", route_next, ["next", END])
    graph.add_conditional_edges("fail_lesson", route_next, ["next", END])
    return graph

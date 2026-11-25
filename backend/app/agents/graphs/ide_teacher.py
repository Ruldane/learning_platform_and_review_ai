"""Graph `ide_teacher` (10.A3): the IDE teacher. One node, one model call
per trigger.

START -> teach -> END

No interruption, no loop. Started only by `POST /ide/sessions/{id}/teach`
(`ROUTE_ONLY`), which applies the cost gate (triggers, caps, anti-repetition, one
call at a time) before starting the session."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.professor import make_teach
from app.agents.runtime.deps import GraphDeps
from app.agents.state.ide_teacher import IdeTeacherState

__all__ = ["IdeTeacherInput", "build"]


class IdeTeacherInput(BaseModel):
    ide_session_id: str = Field(min_length=1, max_length=36)
    trigger: Literal["run_error", "run_ok", "question", "hint", "idle"]
    question: str | None = Field(default=None, max_length=2_000)
    file_path: str | None = Field(default=None, max_length=200)
    line: int | None = Field(default=None, ge=1)
    run_id: str | None = Field(default=None, max_length=36)
    error_key: str | None = Field(default=None, max_length=64)  # set by the gate
    level: int | None = Field(default=None, ge=1, le=3)  # hint level, set by the gate


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(IdeTeacherState)
    graph.add_node("teach", make_teach(deps))
    graph.add_edge(START, "teach")
    graph.add_edge("teach", END)
    return graph

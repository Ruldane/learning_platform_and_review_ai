"""`replan` graph (SPEC F13, D105): the Strategist proposes a replan after the weekly review
or a message from January ("this week I only have 5 hours"), or when January adds skills from
a posting to the schedule (`gap` trigger, D123: no option, additions only in the "Skills from
postings" module), the code fits it in the budget, January accepts it, refuses it or asks for
another proposal.

START -> context -> (options ? ask_option : propose); `gap` trigger: propose (D123)
ask_option -> propose (invalid answer: ask_option)
propose -> preview -> (impossible, or nothing to change without an option ? finalize : ask_accept)
ask_accept: accept -> apply -> (stale ? propose : finalize); refuse -> refuse -> finalize;
             revise (note) -> propose; invalid answer -> ask_accept
finalize -> END

Two stopping points (`ask_option`, `ask_accept`), each alone in its node (SPEC 9.4). The
port writes (`preview`, `apply`, `refuse`) are idempotent."""

from typing import Annotated, Any, Self

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from app.agents.nodes.strategist.replan import (
    ask_accept,
    ask_option,
    finalize,
    make_apply,
    make_context,
    make_preview,
    make_propose,
    make_refuse,
    route_accept,
    route_apply,
    route_option,
    route_preview,
    route_start,
)
from app.agents.nodes.strategist.replan_steps import (
    ACCEPT_INTERRUPT,
    ACCEPT_REPLAN,
    OPTION_LABELS,
    REPLAN_OPTION,
    STALE_NOTE,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.replan import ReplanState
from app.agents.tools.study_schema import ReplanReading, ReplanTrigger

__all__ = [
    "ACCEPT_INTERRUPT",
    "ACCEPT_REPLAN",
    "OPTION_LABELS",
    "REPLAN_OPTION",
    "STALE_NOTE",
    "ReplanInput",
    "build",
]


class ReplanInput(BaseModel):
    program_id: str = Field(min_length=36, max_length=36)
    trigger: ReplanTrigger
    review_entry_id: str | None = None
    available_minutes: int | None = Field(default=None, ge=60, le=10080)
    message: str | None = Field(default=None, max_length=1000)
    reading: ReplanReading | None = None
    # `gap` trigger only ("Add to the schedule", D123): names of the `to_add` rows.
    skills: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=10
    )

    @model_validator(mode="after")
    def _review_of_weekly(self) -> Self:
        """The weekly review needs its entry (422 `invalid_input` otherwise)."""
        if self.trigger == "weekly_review" and self.review_entry_id is None:
            raise ValueError("A review replan needs `review_entry_id`.")
        return self

    @model_validator(mode="after")
    def _skills_of_gap(self) -> Self:
        """Skills with the `gap` trigger, and with it alone."""
        if (self.trigger == "gap") != bool(self.skills):
            raise ValueError("`skills` goes with the `gap` trigger, and only with it.")
        return self

    @model_validator(mode="after")
    def _selected_reading(self) -> Self:
        if (self.trigger == "reading") != (self.reading is not None):
            raise ValueError("A reading goes only with the reading trigger.")
        return self


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ReplanState)
    graph.add_node("context", make_context(deps))
    graph.add_node("ask_option", ask_option)
    graph.add_node("propose", make_propose(deps))
    graph.add_node("preview", make_preview(deps))
    graph.add_node("ask_accept", ask_accept)
    graph.add_node("apply", make_apply(deps))
    graph.add_node("refuse", make_refuse(deps))
    graph.add_node("finalize", finalize)
    for source, target in [
        (START, "context"),
        ("propose", "preview"),
        ("refuse", "finalize"),
        ("finalize", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("context", route_start, ["ask_option", "propose"])
    graph.add_conditional_edges("ask_option", route_option, ["ask_option", "propose"])
    graph.add_conditional_edges("preview", route_preview, ["ask_accept", "finalize"])
    graph.add_conditional_edges(
        "ask_accept", route_accept, ["ask_accept", "apply", "refuse", "propose"]
    )
    graph.add_conditional_edges("apply", route_apply, ["propose", "finalize"])
    return graph

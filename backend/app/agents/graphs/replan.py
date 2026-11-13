"""Parcours `replan` (SPEC F13, D105) : le Stratège propose une replanification après le bilan
hebdomadaire ou un message de January (« cette semaine je n'ai que 5 heures »), le code la range
dans le budget, January l'accepte, la refuse ou demande une autre proposition.

START -> context -> (options ? ask_option : propose)
ask_option -> propose (réponse invalide : ask_option)
propose -> preview -> (impossible, ou rien à changer sans option ? finalize : ask_accept)
ask_accept : accept -> apply -> (périmée ? propose : finalize) ; refuse -> refuse -> finalize ;
             revise (note) -> propose ; réponse invalide -> ask_accept
finalize -> END

Deux points d'arrêt (`ask_option`, `ask_accept`), chacun seul dans son nœud (SPEC 9.4). Les
écritures du port (`preview`, `apply`, `refuse`) sont idempotentes."""

from typing import Any, Self

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
from app.agents.tools.study_schema import ReplanTrigger

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

    @model_validator(mode="after")
    def _review_of_weekly(self) -> Self:
        """Le bilan hebdomadaire demande son entrée (422 `invalid_input` sinon)."""
        if self.trigger == "weekly_review" and self.review_entry_id is None:
            raise ValueError("Une replanification du bilan demande `review_entry_id`.")
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

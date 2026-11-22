from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Interrupt

from app.agents.runtime.played_model import PlayedChat


class LessonState(TypedDict):
    text: str


def _render(interruption: Interrupt, text: str) -> Command[object]:
    brief = interruption.value["brief"]
    delivery = {
        "response": text,
        "step_id": brief["step_id"],
        "fingerprint": brief["fingerprint"],
    }
    return Command(resume={interruption.id: delivery})


def test_saved_old_attempts_request_a_new_brief_without_using_their_answers() -> None:
    version = "Première consigne"
    model = PlayedChat(role="writer", refresh_changed_brief=True)

    def write(_state: LessonState) -> LessonState:
        response = model.invoke(version).content
        if response == "À reprendre":
            response = model.invoke(f"{version} corrigée").content
        return {"text": str(response)}

    graph = StateGraph(LessonState)
    graph.add_node("write", write)
    graph.add_edge(START, "write").add_edge("write", END)
    checkpoints = InMemorySaver()
    compiled = graph.compile(checkpointer=checkpoints)
    cfg: RunnableConfig = {"configurable": {"thread_id": "lesson"}}

    first = compiled.invoke({"text": ""}, cfg)["__interrupt__"][0]
    old = compiled.invoke(_render(first, "À reprendre"), cfg)["__interrupt__"][0]
    assert old.value["brief"]["step_id"] != first.value["brief"]["step_id"]
    version = "Nouvelle consigne"
    restarted = graph.compile(checkpointer=checkpoints)
    refreshed = restarted.invoke(_render(old, "Réponse au vieux brief"), cfg)["__interrupt__"][0]
    brief = refreshed.value["brief"]
    assert brief["step_id"] not in {first.value["brief"]["step_id"], old.value["brief"]["step_id"]}
    assert brief["messages"] == [{"role": "human", "content": version}]
    after_restart = graph.compile(checkpointer=checkpoints)
    assert (
        after_restart.invoke(_render(refreshed, "Nouveau chapitre"), cfg)["text"]
        == "Nouveau chapitre"
    )

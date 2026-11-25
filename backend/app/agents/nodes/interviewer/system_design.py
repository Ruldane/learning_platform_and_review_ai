from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import ValidationError

from app.agents.nodes.interviewer.common import AGENT
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.interview import InterviewState
from app.agents.tools.system_design_port import SystemDesignReview, SystemDesignSubmission
from app.providers.llm.limits import with_output_limit


class Node(Protocol):
    async def __call__(self, state: InterviewState) -> InterviewState: ...


def ask_design(state: InterviewState) -> InterviewState:
    received = interrupt(
        {
            "kind": "system_design_submission",
            "question": "Submit your saved diagram and explain your design choices.",
        }
    )
    try:
        submission = SystemDesignSubmission.model_validate(received)
    except ValidationError:
        return {"design_submission": None}
    return {"design_submission": submission.model_dump(mode="json")}


def design_submitted(state: InterviewState) -> bool:
    return state.get("design_submission") is not None


def make_review_design(deps: GraphDeps) -> Node:
    @node_timeout()
    async def review(state: InterviewState) -> InterviewState:
        submission = SystemDesignSubmission.model_validate(state["design_submission"])
        context = await deps.ports.interviews.freeze_design(
            deps.user_id, deps.session_id, state["interview_id"], submission
        )
        requirements = "\n".join(f"- {item}" for item in context.requirements)
        data = (
            f"Topic: {context.title}\n{context.situation}\n{requirements}\n\n"
            + untrusted(context.diagram, "saved diagram")
            + "\n\n"
            + untrusted(context.defense, "design rationale")
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        assessment = await structured_call(
            with_output_limit(model, 1600),
            SystemDesignReview,
            [SystemMessage(render_prompt("system_design")), HumanMessage(data)],
            agent=AGENT,
            step="critique_architecture",
            intent="Reviewing your diagram and design choices.",
            retries=0,
        )
        return {"design_review": assessment.model_dump(mode="json")}

    return review


def make_save_design(deps: GraphDeps) -> Node:
    async def save(state: InterviewState) -> InterviewState:
        await deps.ports.interviews.save_design_review(
            deps.user_id,
            deps.session_id,
            state["interview_id"],
            SystemDesignReview.model_validate(state["design_review"]),
        )
        return {"summary": "System design review saved."}

    return save

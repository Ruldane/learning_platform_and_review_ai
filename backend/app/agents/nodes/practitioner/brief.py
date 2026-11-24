"""Read module inputs and draft and save a small project brief (P1, D165).

The prompt wraps the module, lesson excerpt, weekly deliverable, and target role as
untrusted data (SPEC 17.4). An invalid model response or provider error records
`brief_failed`, which the user can retry. Logs use IDs, counts, and codes (SPEC 17.2).
"""

import asyncio
import logging

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphInterrupt

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.project_brief import Node, ProjectBriefState
from app.agents.tools.project_port import LESSON_EXCERPT_MAX, BriefInputs
from app.agents.tools.project_schema import ProjectBrief
from app.core.errors import AppError

__all__ = ["ASK", "SUMMARY", "make_close", "make_load", "make_save", "make_write"]

AGENT = "practitioner"
ASK = "Write the project brief."
SUMMARY = "The project brief is ready."
NONE = "(none)"
BUDGET_S = 100.0  # Leave time to store a failure before the node times out.
LANGUAGES = {"fr": "French", "en": "English"}

logger = logging.getLogger(__name__)


def _names(items: list[str]) -> str:
    return "\n".join(f"- {' '.join(item.split())}" for item in items) or NONE


def prompt_of(inputs: BriefInputs) -> str:
    """Wrap the module inputs separately and limit the lesson excerpt."""
    excerpt = (inputs.lesson_excerpt or NONE)[:LESSON_EXCERPT_MAX]
    return render_prompt(
        AGENT,
        mode="project_brief",
        module=untrusted(" ".join(inputs.module_title.split()), "module title"),
        skills=untrusted(_names(inputs.skills), "module skills"),
        prerequisites=untrusted(_names(inputs.prerequisites), "module prerequisites"),
        excerpt=untrusted(excerpt, "lesson excerpt"),
        deliverable_week=untrusted(inputs.week_deliverable or NONE, "weekly deliverable"),
        role=untrusted(inputs.role or NONE, "target role"),
        language=LANGUAGES[inputs.language],
    )


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: ProjectBriefState) -> ProjectBriefState:
        inputs = await deps.ports.projects.brief_inputs(deps.user_id, state["project_id"])
        logger.info(
            "Brief inputs: session %s, project %s, %d skills, lesson excerpt %s",
            deps.session_id,
            state["project_id"],
            len(inputs.skills),
            inputs.lesson_excerpt is not None,
        )
        return {}

    return load


def make_write(deps: GraphDeps) -> Node:
    @node_timeout()
    async def write(state: ProjectBriefState) -> ProjectBriefState:
        project_id = state["project_id"]
        ports = deps.ports.projects
        inputs = await ports.brief_inputs(deps.user_id, project_id)
        messages: list[BaseMessage] = [SystemMessage(prompt_of(inputs)), HumanMessage(ASK)]
        try:
            async with asyncio.timeout(BUDGET_S):  # plus court que le plafond du nœud : rangé
                tier = get_agent(AGENT).tier
                model = await deps.models.get_chat_model(deps.user_id, tier, agent=AGENT)
                brief = await structured_call(
                    model,
                    ProjectBrief,
                    messages,
                    agent=AGENT,
                    step="enonce",
                    intent="writing the project brief",
                )
        except GraphInterrupt:
            raise
        except Exception as exc:  # l'échec est rangé (un code), puis le parcours s'arrête
            timed_out = isinstance(exc, TimeoutError)
            code = (
                "node_timeout"
                if timed_out
                else exc.code
                if isinstance(exc, AppError)
                else type(exc).__name__
            )
            logger.info(
                "Brief failed: session %s, project %s, cause %s",
                deps.session_id,
                project_id,
                code,
            )
            await ports.brief_failed(deps.user_id, deps.session_id, project_id, code)
            if timed_out:
                raise AppError(
                    "node_timeout",
                    f"Writing the project brief took over {BUDGET_S:g} seconds.",
                    504,
                ) from None
            raise
        return {"brief": brief.model_dump()}

    return write


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: ProjectBriefState) -> ProjectBriefState:
        brief = ProjectBrief.model_validate(state["brief"])
        await deps.ports.projects.save_brief(
            deps.user_id, deps.session_id, state["project_id"], brief
        )
        logger.info(
            "Brief saved: session %s, project %s, %d criteria, %d hours",
            deps.session_id,
            state["project_id"],
            len(brief.criteria),
            brief.hours,
        )
        return {}

    return save


def make_close(deps: GraphDeps) -> Node:
    @node_timeout()
    async def close(state: ProjectBriefState) -> ProjectBriefState:
        return {"summary": SUMMARY}

    return close

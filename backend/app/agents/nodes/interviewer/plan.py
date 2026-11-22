"""L'Intervieweur prépare l'entretien (SPEC F10, D145) : `load` lit le contexte par le port, `plan`
écrit les questions principales (offre, dossier, CV envoyé, écarts connus) selon le mode, la
langue et la durée.

`plan` est le seul nœud qui pose la première question ; rejoué après un arrêt, il redemande (rien
n'est écrit). Une fois le plan dans l'état (checkpointer), il n'est plus jamais redemandé : une
question en attente reste la même au redémarrage. Journaux : identifiants et nombres seulement,
jamais une question, une réponse, l'entreprise ni le poste (17.2)."""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.interviewer.common import AGENT, Node, context_of, say_question
from app.agents.nodes.interviewer.context import (
    MODE_GUIDES,
    cv_block,
    dossier_block,
    gaps_block,
    head_vars,
    posting_block,
    profile_block,
)
from app.agents.nodes.interviewer.salary import salary_questions
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import (
    QUESTIONS_BY_DURATION,
    InterviewContext,
    plan_schema,
)

PLAN_REQUEST = "Prépare les questions de l'entretien."
PLAN_TIMEOUT_S = 300  # trois demandes au plus, chacune avec ses nouveaux essais (GLM)

logger = logging.getLogger(__name__)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: InterviewState) -> InterviewState:
        ctx = await deps.ports.interviews.context(deps.user_id, state["interview_id"])
        logger.info(
            "Entretien lu : session %s, entretien %s, mode %s, %d min",
            deps.session_id,
            state["interview_id"],
            ctx.mode,
            ctx.duration_min,
        )
        return {"context": ctx.model_dump(mode="json")}

    return load


def plan_vars(ctx: InterviewContext, count: int) -> dict[str, Any]:
    return {
        **head_vars(ctx),
        "mode": "plan",
        "count": count,
        "mode_guide": MODE_GUIDES[ctx.mode],
        "posting": posting_block(ctx),
        "dossier": dossier_block(ctx),
        "cv": cv_block(ctx),
        "gaps": gaps_block(ctx),
        "profile": profile_block(ctx),
    }


def make_plan(deps: GraphDeps) -> Node:
    @node_timeout(PLAN_TIMEOUT_S)
    async def plan(state: InterviewState) -> InterviewState:
        """Les questions principales (exactement `QUESTIONS_BY_DURATION`), puis la première."""
        ctx = context_of(state)
        count = 3 if ctx.surprise else QUESTIONS_BY_DURATION[ctx.duration_min]
        if ctx.salary is not None:
            questions = [
                question.model_dump()
                for question in salary_questions(ctx.salary, ctx.language, count)
            ]
        else:
            model = await deps.models.get_chat_model(
                deps.user_id, get_agent(AGENT).tier, agent=AGENT
            )
            prompt = render_prompt(AGENT, **plan_vars(ctx, count))
            planned = await structured_call(
                model,
                plan_schema(count),
                [SystemMessage(prompt), HumanMessage(PLAN_REQUEST)],
                agent=AGENT,
                step="plan",
                intent="je prépare tes questions",
            )
            questions = [question.model_dump() for question in planned.questions]
        logger.info("Plan écrit : session %s, %d question(s)", deps.session_id, len(questions))
        say_question(1, questions[0]["text"])
        return {
            "plan": questions,
            "position": 0,
            "current": questions[0]["text"],
            "follow_up_open": False,
            "exchanges": [],
        }

    return plan

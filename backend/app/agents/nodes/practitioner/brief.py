"""Le Praticien écrit l'énoncé d'un mini projet (P1, D165) : `load` relit les entrées du module par
le port, `write` appelle le modèle (un appel standard), `save` range l'énoncé.

Le titre du module, ses compétences et prérequis, l'extrait de la leçon, le livrable de la semaine
et le poste visé sont des données (leçon écrite par un agent d'après le web, objectif de January) :
chacun est encadré par `untrusted` (17.4). Une sortie invalide, ou toute autre panne du modèle,
range l'échec par le port (`brief_failed`, un code) puis arrête le parcours : `run.failed` dit la
cause, « Réessayer » relance. Journaux : identifiants, nombres et codes, jamais un énoncé (17.2)."""

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
ASK = "Écris l'énoncé du projet."
SUMMARY = "Énoncé du projet prêt."
NONE = "(aucun)"
BUDGET_S = 100.0  # plus court que `node_timeout` (120 s) : un dépassement est rangé par le port
LANGUAGES = {"fr": "français", "en": "anglais"}

logger = logging.getLogger(__name__)


def _names(items: list[str]) -> str:
    return "\n".join(f"- {' '.join(item.split())}" for item in items) or NONE


def prompt_of(inputs: BriefInputs) -> str:
    """Le prompt de l'énoncé : chaque donnée du module encadrée comme contenu non fiable (l'extrait
    de leçon est coupé à `LESSON_EXCERPT_MAX` caractères)."""
    excerpt = (inputs.lesson_excerpt or NONE)[:LESSON_EXCERPT_MAX]
    return render_prompt(
        AGENT,
        mode="project_brief",
        module=untrusted(" ".join(inputs.module_title.split()), "titre du module"),
        skills=untrusted(_names(inputs.skills), "compétences du module"),
        prerequisites=untrusted(_names(inputs.prerequisites), "prérequis du module"),
        excerpt=untrusted(excerpt, "extrait de la leçon"),
        deliverable_week=untrusted(inputs.week_deliverable or NONE, "livrable de la semaine"),
        role=untrusted(inputs.role or NONE, "poste visé"),
        language=LANGUAGES[inputs.language],
    )


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: ProjectBriefState) -> ProjectBriefState:
        inputs = await deps.ports.projects.brief_inputs(deps.user_id, state["project_id"])
        logger.info(
            "Énoncé : session %s, projet %s, %d compétence(s), extrait de leçon %s",
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
                    intent="j'écris l'énoncé du projet",
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
                "Énoncé impossible : session %s, projet %s, cause %s",
                deps.session_id,
                project_id,
                code,
            )
            await ports.brief_failed(deps.user_id, deps.session_id, project_id, code)
            if timed_out:
                raise AppError(
                    "node_timeout", f"L'étape write a dépassé {BUDGET_S:g} secondes.", 504
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
            "Énoncé rangé : session %s, projet %s, %d critère(s), %d heure(s)",
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

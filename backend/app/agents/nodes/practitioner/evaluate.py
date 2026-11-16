"""Le Praticien évalue le rendu d'un mini projet (P2, P3, D165) : `load`, `read_repo`, puis `skip`
(rien à lire) ou `evaluate`.

- `read_repo` : un lien de dépôt → `repo_text` (une page), coupé à 8 000 caractères ; une page
  qui ne se lit pas, une panne ou un texte vide : `unreadable` (la classe de l'exception seule est
  journalisée). Sans lien : `none`.
- Sans description **ni** dépôt lisible, rien n'est évalué : `skip` range « à reprendre » sans appel
  au modèle (jamais « validé » sur rien).
- `evaluate` : un appel standard ; l'énoncé et les critères numérotés sont du code de Tremplin, la
  description de January et le README sont encadrés par `untrusted` (17.4) ; les captures ne sont
  pas envoyées (P2) et le prompt le dit. **Le verdict est calculé par le code** (`verdict`), jamais
  par le modèle.

Journaux : identifiants, nombres et codes, jamais un texte du projet (17.2)."""

import logging
from typing import Any, Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.practitioner.outcome import to_state
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.project_review import Node, ProjectReviewState
from app.agents.tools.project_port import ReviewInputs, ReviewOutcome
from app.agents.tools.project_schema import ProjectEvaluation, settled_results, verdict

__all__ = [
    "ASK",
    "NO_REPO_FEEDBACK",
    "README_MAX",
    "make_evaluate",
    "make_load",
    "make_read_repo",
    "make_skip",
    "route_evaluate",
    "route_read",
]

AGENT = "practitioner"
ASK = "Évalue le rendu du projet."
README_MAX = 8_000
NO_REPO_FEEDBACK = "Je n'ai pas pu lire ton dépôt : ajoute une description de ce que tu as fait."
NONE = "(aucun)"
LANGUAGES = {"fr": "français", "en": "anglais"}
REPO_NOTES = {
    "read": "Le README du dépôt de January a été lu : il figure ci-dessus.",
    "unreadable": "Le dépôt de January n'a pas pu être lu : n'évalue que sur sa description.",
    "none": "January n'a donné aucun dépôt : n'évalue que sur sa description.",
}

logger = logging.getLogger(__name__)


def _lines(items: list[str], *, numbered: bool = False) -> str:
    return "\n".join(
        f"{rank}. {item}" if numbered else f"- {item}" for rank, item in enumerate(items, start=1)
    )


def prompt_of(
    inputs: ReviewInputs, repo_text: str | None, repo_status: Literal["read", "unreadable", "none"]
) -> str:
    brief = inputs.brief
    notes = [REPO_NOTES[repo_status]]
    if inputs.screenshots:
        notes.append(
            f"January a joint {inputs.screenshots} capture(s) d'écran : tu ne les vois pas, ne les "
            "compte ni pour ni contre."
        )
    return render_prompt(
        AGENT,
        mode="project_review",
        title=brief.title,
        context=brief.context,
        objective=brief.objective,
        constraints=_lines(brief.constraints),
        criteria=_lines(brief.criteria, numbered=True),
        count=len(brief.criteria),
        description=untrusted(inputs.description or NONE, "description de January"),
        readme=untrusted(repo_text, "README du dépôt") if repo_text else "README : non lu.",
        notes="\n".join(notes),
        language=LANGUAGES[inputs.language],
    )


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: ProjectReviewState) -> ProjectReviewState:
        inputs = await deps.ports.projects.review_inputs(deps.user_id, state["project_id"])
        logger.info(
            "Rendu lu : session %s, projet %s, %d critère(s), dépôt %s, description %s, "
            "%d capture(s)",
            deps.session_id,
            state["project_id"],
            len(inputs.brief.criteria),
            inputs.repo_url is not None,
            bool((inputs.description or "").strip()),
            inputs.screenshots,
        )
        return {"title": inputs.brief.title}

    return load


def make_read_repo(deps: GraphDeps) -> Node:
    @node_timeout()
    async def read_repo(state: ProjectReviewState) -> ProjectReviewState:
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        text: str | None = None
        status: Literal["read", "unreadable", "none"] = "none"
        if inputs.repo_url:
            try:
                text = await deps.ports.projects.repo_text(
                    deps.user_id, deps.session_id, inputs.repo_url
                )
            except Exception as exc:  # un dépôt illisible n'arrête pas l'évaluation
                logger.info(
                    "Dépôt illisible : session %s, projet %s, cause %s",
                    deps.session_id,
                    project_id,
                    type(exc).__name__,
                )
            text = (text or "").strip()[:README_MAX] or None
            status = "read" if text else "unreadable"
        logger.info(
            "Dépôt lu : session %s, projet %s, état %s, %d caractère(s)",
            deps.session_id,
            project_id,
            status,
            len(text or ""),
        )
        return {
            "repo_text": text,
            "repo_status": status,
            "nothing_to_read": status != "read" and not (inputs.description or "").strip(),
        }

    return read_repo


def route_read(state: ProjectReviewState) -> str:
    return "skip" if state.get("nothing_to_read") else "evaluate"


def _outcome(
    inputs: ReviewInputs,
    evaluation: ProjectEvaluation | None,
    repo_status: Literal["read", "unreadable", "none"],
) -> dict[str, Any]:
    count = len(inputs.brief.criteria)
    results = evaluation.results if evaluation else []
    return to_state(
        ReviewOutcome(
            verdict=verdict(count, results),
            results=settled_results(count, results),
            feedback=evaluation.feedback if evaluation else NO_REPO_FEEDBACK,
            repo_status=repo_status,
            drafts=None,
        )
    )


def make_skip(deps: GraphDeps) -> Node:
    @node_timeout()
    async def skip(state: ProjectReviewState) -> ProjectReviewState:
        """Ni description ni dépôt lisible : « à reprendre », sans appel au modèle."""
        inputs = await deps.ports.projects.review_inputs(deps.user_id, state["project_id"])
        logger.info("Rien à évaluer : session %s, projet %s", deps.session_id, state["project_id"])
        return {"outcome": _outcome(inputs, None, state.get("repo_status", "none"))}

    return skip


def make_evaluate(deps: GraphDeps) -> Node:
    @node_timeout()
    async def evaluate(state: ProjectReviewState) -> ProjectReviewState:
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        status = state.get("repo_status", "none")
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        prompt = prompt_of(inputs, state.get("repo_text"), status)
        messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(ASK)]
        evaluation = await structured_call(
            model,
            ProjectEvaluation,
            messages,
            agent=AGENT,
            step="evaluation",
            intent="j'évalue le rendu du projet",
        )
        outcome = _outcome(inputs, evaluation, status)
        logger.info(
            "Rendu évalué : session %s, projet %s, %d résultat(s) rendu(s), verdict %s",
            deps.session_id,
            project_id,
            len(evaluation.results),
            outcome["verdict"],
        )
        return {"outcome": outcome}

    return evaluate


def route_evaluate(state: ProjectReviewState) -> str:
    return "drafts" if state["outcome"]["verdict"] == "validated" else "save"

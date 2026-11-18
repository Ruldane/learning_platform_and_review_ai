"""Le Praticien écrit les quatre brouillons d'un projet validé (P3, P4, D165) : une ligne de CV,
l'entrée de projet du profil, un post LinkedIn et le plan du README. Un appel standard, au nom
de January : le code contrôle chaque texte, jamais le modèle.

- `text_claims(draft_text(kind), project_reference(...), allowed=[titre de l'énoncé])` : les
  chiffres, outils, titres et noms propres que ni le profil validé, ni ce que January dit de son
  projet, ni les compétences du module ne disent. Le README du dépôt n'est **jamais** une référence
  (texte web) et n'est pas montré au modèle ;
- le post LinkedIn compte 80 à 200 mots, comptés par le code.

Un brouillon fautif repart au modèle **une seule fois**, avec tous les termes nommés (et la
longueur) ; les brouillons déjà propres sont gardés. Ce qui reste après l'essai est rangé « à
vérifier » avec ses termes (`flags`). Le nouvel essai est un nœud à part (`redo`, son propre
délai) : toute panne, quelle qu'elle soit, garde le premier jet « à vérifier ». L'évaluation
validée n'est pas perdue. Le premier appel a lui aussi son propre délai (`DRAFTS_BUDGET_S`) : s'il
échoue (fournisseur, format, plafond de jetons, délai), l'évaluation validée est rangée **sans
brouillons** (« brouillons indisponibles »), jamais perdue (D173, D165 n° 5).

Journaux : identifiants et nombres, jamais un brouillon ni un terme (17.2)."""

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphInterrupt

from app.agents.nodes.practitioner.outcome import from_state, to_state
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.project_review import Node, ProjectReviewState
from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.project_port import DraftResult, ReviewInputs
from app.agents.tools.project_schema import (
    DRAFT_KINDS,
    LINKEDIN_WORDS,
    DraftKind,
    ProjectDrafts,
    draft_text,
    linkedin_words,
    project_fact,
    project_reference,
)
from app.agents.tools.text_claims import text_claims
from app.core.errors import AppError

__all__ = [
    "ASK",
    "Problems",
    "check",
    "make_drafts",
    "make_redo",
    "results_of",
    "retry_message",
    "route_drafts",
]

AGENT = "practitioner"
ASK = "Écris les brouillons du projet."
NONE = "(aucun)"
RETRY_BUDGET_S = 90.0  # son propre délai, plus court que `node_timeout` (120 s)
DRAFTS_BUDGET_S = 100.0  # le premier appel : son propre délai, sous `node_timeout`
LANGUAGES = {"fr": "français", "en": "anglais"}
RETRY = (
    "Ces éléments ne figurent ni dans la description de January, ni dans les compétences du "
    "module, ni dans le titre de l'énoncé : {terms}. Réécris sans eux les brouillons concernés "
    "({kinds}), avec ce que January a dit seulement (l'objectif de l'énoncé n'autorise "
    "aucun terme)."
)
LENGTH_RETRY = "Le post LinkedIn fait {words} mots : il doit en faire de {low} à {high}."

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Problems:
    terms: list[str]  # ce que la référence ne dit pas
    words: int | None  # les mots du post LinkedIn quand ils sont hors bornes

    def __bool__(self) -> bool:
        return bool(self.terms or self.words is not None)

    def flags(self) -> list[str]:
        """Les termes, puis la longueur du post quand elle est hors bornes."""
        low, high = LINKEDIN_WORDS
        length = [] if self.words is None else [f"{self.words} mots ({low} à {high} attendus)"]
        return [*self.terms, *length]


def check(
    drafts: ProjectDrafts, reference: MasterProfileData, title: str
) -> dict[DraftKind, Problems]:
    """Les problèmes de chaque brouillon, dans l'ordre des types (vides : `bool(...)` faux)."""
    found: dict[DraftKind, Problems] = {}
    low, high = LINKEDIN_WORDS
    for kind in DRAFT_KINDS:
        text = draft_text(kind, drafts)
        terms = list(dict.fromkeys(c.term for c in text_claims(text, reference, allowed=[title])))
        count = linkedin_words(text) if kind == "linkedin_post" else low
        found[kind] = Problems(terms, None if low <= count <= high else count)
    return found


def retry_message(found: dict[DraftKind, Problems]) -> str:
    """Le nouvel essai : tous les termes nommés, la longueur du post si elle est hors bornes."""
    flagged = {kind: problems for kind, problems in found.items() if problems}
    terms = list(dict.fromkeys(term for problems in flagged.values() for term in problems.terms))
    parts = []
    if terms:
        kinds = ", ".join(kind for kind, problems in flagged.items() if problems.terms)
        parts.append(RETRY.format(terms=", ".join(terms), kinds=kinds))
    words = flagged["linkedin_post"].words if "linkedin_post" in flagged else None
    if words is not None:
        low, high = LINKEDIN_WORDS
        parts.append(LENGTH_RETRY.format(words=words, low=low, high=high))
    return "\n".join(parts)


def results_of(drafts: ProjectDrafts, found: dict[DraftKind, Problems]) -> list[DraftResult]:
    return [
        DraftResult(
            kind=kind,
            content=draft_text(kind, drafts),
            entry=drafts.profile_entry if kind == "profile_entry" else None,
            status="to_check" if found[kind] else "ready",
            flags=found[kind].flags(),
        )
        for kind in DRAFT_KINDS
    ]


def prompt_of(inputs: ReviewInputs) -> str:
    """Seuls la description, les compétences du module et le titre permettent un terme ; le titre,
    l'objectif (écrits par un modèle) et les compétences sont encadrés comme données."""
    return render_prompt(
        AGENT,
        mode="project_drafts",
        title=untrusted(" ".join(inputs.brief.title.split()), "titre de l'énoncé"),
        objective=untrusted(" ".join(inputs.brief.objective.split()), "objectif de l'énoncé"),
        skills=untrusted(", ".join(inputs.skills) or NONE, "compétences du module"),
        description=untrusted(inputs.description or NONE, "description de January"),
        language=LANGUAGES[inputs.language],
    )


def _reference(inputs: ReviewInputs) -> MasterProfileData:
    fact = project_fact(inputs.brief.title, inputs.description, inputs.skills, inputs.repo_url)
    return project_reference(inputs.profile, fact, inputs.skills)


async def _model(deps: GraphDeps) -> BaseChatModel:
    return await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)


def _stored(
    state: ProjectReviewState, drafts: ProjectDrafts, found: dict[DraftKind, Problems]
) -> dict[str, Any]:
    outcome = from_state(state["outcome"])
    return to_state(replace(outcome, drafts=results_of(drafts, found)))


def make_drafts(deps: GraphDeps) -> Node:
    """Le premier jet, contrôlé et rangé dans l'état (`to_check` avec ses termes) ; le nouvel
    essai est un nœud à part (`redo`), avec son propre délai (D165)."""

    @node_timeout()
    async def drafts(state: ProjectReviewState) -> ProjectReviewState:
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        messages: list[BaseMessage] = [SystemMessage(prompt_of(inputs)), HumanMessage(ASK)]
        try:
            async with asyncio.timeout(DRAFTS_BUDGET_S):
                first = await structured_call(
                    await _model(deps),
                    ProjectDrafts,
                    messages,
                    agent=AGENT,
                    step="brouillons",
                    intent="j'écris les brouillons du projet",
                )
        except GraphInterrupt:
            raise
        except Exception as exc:  # les brouillons sont facultatifs : l'évaluation validée reste
            logger.info(
                "Brouillons impossibles : session %s, projet %s, cause %s",
                deps.session_id,
                project_id,
                _code(exc),
            )
            outcome = from_state(state["outcome"])
            return {"outcome": to_state(replace(outcome, drafts=[])), "retry_needed": False}
        found = check(first, _reference(inputs), inputs.brief.title)
        logger.info(
            "Brouillons écrits : session %s, projet %s, %d à vérifier avant le nouvel essai",
            deps.session_id,
            project_id,
            sum(bool(problems) for problems in found.values()),
        )
        return {
            "outcome": _stored(state, first, found),
            "first_drafts": first.model_dump(),
            "retry_needed": any(found.values()),
        }

    return drafts


def route_drafts(state: ProjectReviewState) -> str:
    return "redo" if state.get("retry_needed") else "save"


def _code(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "node_timeout"
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


def make_redo(deps: GraphDeps) -> Node:
    @node_timeout()
    async def redo(state: ProjectReviewState) -> ProjectReviewState:
        """Garde le premier jet et l'évaluation validée si la correction échoue."""
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        reference, title = _reference(inputs), inputs.brief.title
        first = ProjectDrafts.model_validate(state["first_drafts"])
        found = check(first, reference, title)
        if not any(found.values()):  # reprise : plus rien à corriger, aucun message vide au modèle
            logger.info("Rien à corriger : session %s, projet %s", deps.session_id, project_id)
            return {"outcome": _stored(state, first, found)}
        conversation: list[BaseMessage] = [
            SystemMessage(prompt_of(inputs)),
            HumanMessage(ASK),
            AIMessage(first.model_dump_json()),
            HumanMessage(retry_message(found)),
        ]
        try:
            async with asyncio.timeout(RETRY_BUDGET_S):
                second = await structured_call(
                    await _model(deps),
                    ProjectDrafts,
                    conversation,
                    agent=AGENT,
                    step="brouillons-2",
                    intent="je corrige les brouillons du projet",
                )
        except GraphInterrupt:
            raise
        except Exception as exc:  # le premier jet reste rangé, `to_check`
            logger.info(
                "Nouvel essai des brouillons impossible : session %s, projet %s, cause %s",
                deps.session_id,
                project_id,
                _code(exc),
            )
            return {}
        fixed: dict[str, Any] = {k: getattr(second, k) for k in found if found[k]}
        final = first.model_copy(update=fixed)
        again = check(final, reference, title)
        logger.info(
            "Brouillons corrigés : session %s, projet %s, %d à vérifier",
            deps.session_id,
            project_id,
            sum(bool(problems) for problems in again.values()),
        )
        return {"outcome": _stored(state, final, again)}

    return redo

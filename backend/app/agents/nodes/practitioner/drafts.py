"""Le Praticien écrit les quatre brouillons d'un projet validé (P3, P4, D165) : une ligne de CV,
l'entrée de projet du profil, un post LinkedIn et le plan du README. Un seul appel standard, au nom
de January : le code contrôle chaque texte, jamais le modèle.

- `text_claims(draft_text(kind), project_reference(...), allowed=[titre de l'énoncé])` : les
  chiffres, outils, titres et noms propres que ni le profil validé, ni ce que January dit de son
  projet, ni les compétences du module ne disent. Le README du dépôt n'est **jamais** une référence
  (texte web) et n'est pas montré au modèle ;
- le post LinkedIn compte 80 à 200 mots, comptés par le code.

Un brouillon fautif repart au modèle **une seule fois**, avec tous les termes nommés (et la
longueur) ; les brouillons déjà propres sont gardés. Ce qui reste après l'essai est rangé « à
vérifier » avec ses termes (`flags`). Si le nouvel essai échoue (format invalide), le premier jet
est gardé « à vérifier » : l'évaluation validée n'est pas perdue.

Journaux : identifiants et nombres, jamais un brouillon ni un terme (17.2)."""

import logging
from dataclasses import dataclass, replace
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

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

__all__ = ["ASK", "Problems", "check", "make_drafts", "results_of", "retry_message"]

AGENT = "practitioner"
ASK = "Écris les brouillons du projet."
NONE = "(aucun)"
LANGUAGES = {"fr": "français", "en": "anglais"}
RETRY = (
    "Ces éléments ne figurent ni dans ce que January dit de son projet, ni dans l'énoncé, ni dans "
    "les compétences du module : {terms}. Réécris sans eux les brouillons concernés ({kinds}), "
    "avec ce que January a dit seulement."
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
    return render_prompt(
        AGENT,
        mode="project_drafts",
        title=inputs.brief.title,
        objective=inputs.brief.objective,
        skills=", ".join(inputs.skills) or NONE,
        description=untrusted(inputs.description or NONE, "description de January"),
        language=LANGUAGES[inputs.language],
    )


async def _retry(
    deps: GraphDeps,
    model: BaseChatModel,
    messages: list[BaseMessage],
    first: ProjectDrafts,
    found: dict[DraftKind, Problems],
) -> ProjectDrafts | None:
    """Le second jet, ou `None` si le modèle ne rend plus de format valable."""
    conversation = [
        *messages,
        AIMessage(first.model_dump_json()),
        HumanMessage(retry_message(found)),
    ]
    try:
        return await structured_call(
            model,
            ProjectDrafts,
            conversation,
            agent=AGENT,
            step="brouillons-2",
            intent="je corrige les brouillons du projet",
        )
    except AppError as exc:
        if exc.code != "structured_output_invalid":
            raise
        logger.info("Nouvel essai des brouillons refusé : cause %s", exc.code)
        return None


def make_drafts(deps: GraphDeps) -> Node:
    @node_timeout()
    async def drafts(state: ProjectReviewState) -> ProjectReviewState:
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        title = inputs.brief.title
        fact = project_fact(title, inputs.description, inputs.skills, inputs.repo_url)
        reference = project_reference(inputs.profile, fact, inputs.skills)
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        messages: list[BaseMessage] = [SystemMessage(prompt_of(inputs)), HumanMessage(ASK)]
        first = await structured_call(
            model,
            ProjectDrafts,
            messages,
            agent=AGENT,
            step="brouillons",
            intent="j'écris les brouillons du projet",
        )
        final, found = first, check(first, reference, title)
        if any(found.values()):
            second = await _retry(deps, model, messages, first, found)
            if second is not None:
                fixed: dict[str, Any] = {k: getattr(second, k) for k in found if found[k]}
                final = first.model_copy(update=fixed)
                found = check(final, reference, title)
        results = results_of(final, found)
        outcome = from_state(state["outcome"])
        logger.info(
            "Brouillons écrits : session %s, projet %s, %d prêt(s), %d à vérifier",
            deps.session_id,
            project_id,
            sum(r.status == "ready" for r in results),
            sum(r.status == "to_check" for r in results),
        )
        return {"outcome": to_state(replace(outcome, drafts=results))}

    return drafts

"""La confrontation du Lecteur ATS et du Recruteur (SPEC 5.3, D129), deux tours au plus (5.3).

Tour 1 : chaque agent prend position (`Confrontation`) sur les propositions de l'autre : `keep`,
`drop` (contestée), `amend` (texte remplacé, contestée, origine gardée). Tour 2 : les propositions
contestées reviennent à leur auteur (objection, origine, amendement) ; `keep` rend son texte
d'origine, `drop` retire, `amend` pose son nouveau texte, le silence laisse l'amendement. Jamais
de troisième tour ; sinon January tranche. Un texte amendé repasse par le validateur. Une position
sur une référence inconnue, en double, ou un `amend` sans texte est renvoyée au modèle (deux fois
au plus), puis ignorée. Sortie invalide ou délai d'un agent (`STANCE_TIMEOUT_S`, chaque agent a le
sien) : « tout garder » pour cet agent, les propositions déjà obtenues restent et la revue
continue. Débat publié dans le fil, sans écriture de port."""

import asyncio
import logging
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.review_common import author_of, problems_text, review_inputs
from app.agents.nodes.review_debate import AGENTS, debate_text
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.review_schema import Confrontation, Proposal, Stance
from app.core.errors import AppError

CONFRONT_REQUEST = {
    1: "Prends position sur les propositions de l'autre agent.",
    2: "Réponds aux objections sur tes propositions.",
}
MAX_STANCE_ASKS = 3
STANCE_TIMEOUT_S = 420  # les positions d'un agent (demandes et nouveaux essais compris)
CONFRONT_TIMEOUT_S = 2 * STANCE_TIMEOUT_S + 60  # deux agents, puis la marge du nœud
_TEXT_ACTIONS = ("rewrite", "add")
logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def proposals_text(proposals: list[Proposal], critiques: dict[str, dict[str, str]]) -> str:
    """Les propositions à juger, encadrées (17.4) ; au tour 2, avec l'objection de l'autre agent."""
    blocks = []
    for p in proposals:
        cited = ", ".join(p.fact_ids) or "aucun"
        lines = [
            f"{p.ref} — {p.action}, section {p.section}, cible {p.target or '-'}, type {p.type}, "
            f"faits cités : {cited}",
            f"  Texte : {p.after or '(aucun)'}",
            f"  Raison : {p.reason}",
        ]
        if (critique := critiques.get(p.ref)) is not None:
            if original := critique.get("original"):
                lines[1:2] = [
                    f"  Texte d'origine (le tien) : {original}",
                    f"  Texte amendé par l'autre agent : {p.after or '(aucun)'}",
                ]
            lines.append(f"  Objection : {critique['stance']} — {critique['reason']}")
        blocks.append("\n".join(lines))
    return untrusted("\n".join(blocks), "propositions")


def stance_problems(found: Confrontation, by_ref: dict[str, Proposal]) -> list[str]:
    """Défauts renvoyés au modèle ; une référence reçue n'est jamais recopiée (texte libre)."""
    problems: list[str] = []
    seen: set[str] = set()
    allowed = ", ".join(by_ref)
    for stance in found.stances:
        proposal = by_ref.get(stance.ref)
        if proposal is None:
            problems.append(
                f"Une position vise une référence absente de la liste : n'emploie que {allowed}."
            )
            continue
        if stance.ref in seen:
            problems.append(
                f"La référence {stance.ref} a deux positions : une seule par référence."
            )
        seen.add(stance.ref)
        if stance.stance == "amend" and proposal.action not in _TEXT_ACTIONS:
            problems.append(
                f"La proposition {stance.ref} n'écrit aucun texte : choisis `keep` ou `drop`."
            )
        elif stance.stance == "amend" and not (stance.after or "").strip():
            problems.append(
                f"La position sur {stance.ref} propose une autre formulation sans texte : "
                "renseigne `after`."
            )
    return problems


def clean_stances(found: Confrontation, by_ref: dict[str, Proposal]) -> dict[str, Stance]:
    """Les positions valables, la première par référence ; les autres sont ignorées (`keep`)."""
    kept: dict[str, Stance] = {}
    for stance in found.stances:
        if stance.ref in kept or stance_problems(Confrontation(stances=[stance]), by_ref):
            continue
        kept[stance.ref] = stance
    return kept


def apply_first(
    proposals: list[Proposal], stances: dict[str, Stance]
) -> tuple[list[Proposal], dict[str, dict[str, str]]]:
    """Tour 1 : `amend` remplace le texte (l'origine reste dans `contested`, pour le tour 2) ;
    `drop` et `amend` rendent la proposition contestée."""
    out: list[Proposal] = []
    contested: dict[str, dict[str, str]] = {}
    for p in proposals:
        stance = stances.get(p.ref)
        if stance is not None and stance.stance != "keep":
            contested[p.ref] = {"stance": stance.stance, "reason": stance.reason}
            if stance.stance == "amend" and stance.after:
                contested[p.ref]["original"] = p.after or ""
                p = p.model_copy(update={"after": stance.after.strip()})
        out.append(p)
    return out, contested


def apply_second(
    proposals: list[Proposal], contested: dict[str, dict[str, str]], stances: dict[str, Stance]
) -> tuple[list[Proposal], list[str]]:
    """Tour 2, l'auteur : `drop` retire, `keep` rend l'origine, `amend` remplace, silence : rien."""
    out: list[Proposal] = []
    removed: list[str] = []
    for p in proposals:
        stance = stances.get(p.ref)
        kind = stance.stance if stance is not None else "silent"
        if p.ref not in contested or kind == "silent":
            out.append(p)
        elif kind == "drop":
            removed.append(p.ref)
        elif kind == "amend" and stance is not None and stance.after:
            out.append(p.model_copy(update={"after": stance.after.strip()}))
        else:
            original = contested[p.ref].get("original")
            out.append(p if original is None else p.model_copy(update={"after": original}))
    return out, removed


async def _ask(
    deps: GraphDeps, agent: str, round_no: int, variables: dict[str, Any], text: str
) -> Confrontation:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(agent).tier, agent=agent)
    prompt = render_prompt(agent, mode="confront", round=round_no, proposals=text, **variables)
    return await structured_call(
        model,
        Confrontation,
        [SystemMessage(prompt), HumanMessage(CONFRONT_REQUEST[round_no])],
        agent=agent,
        step=f"confrontation-{round_no}",
        intent="stating my position" if round_no == 1 else "replying to objections",
    )


async def ask_stances(
    deps: GraphDeps,
    agent: str,
    round_no: int,
    variables: dict[str, Any],
    judged: list[Proposal],
    critiques: dict[str, dict[str, str]],
) -> dict[str, Stance]:
    """Les positions de `agent` sur `judged`, redemandées deux fois au plus ; `{}` (tout garder)
    si le modèle ne rend pas de sortie valable."""
    by_ref = {p.ref: p for p in judged}
    text = proposals_text(judged, critiques)
    try:
        async with asyncio.timeout(STANCE_TIMEOUT_S):
            found = await _ask(deps, agent, round_no, variables, text)
            for _ in range(MAX_STANCE_ASKS - 1):
                problems = stance_problems(found, by_ref)
                if not problems:
                    break
                found = await _reask(deps, agent, round_no, variables, text, found, problems)
    except TimeoutError:
        logger.info(
            "Confrontation sans réponse à temps : session %s, agent %s", deps.session_id, agent
        )
        return {}
    except AppError as exc:
        if exc.code != "structured_output_invalid":
            raise
        logger.info(
            "Confrontation sans sortie valable : session %s, agent %s", deps.session_id, agent
        )
        return {}
    return clean_stances(found, by_ref)


async def _reask(
    deps: GraphDeps,
    agent: str,
    round_no: int,
    variables: dict[str, Any],
    text: str,
    found: Confrontation,
    problems: list[str],
) -> Confrontation:
    logger.info(
        "Positions redemandées : session %s, agent %s, %d défaut(s)",
        deps.session_id,
        agent,
        len(problems),
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(agent).tier, agent=agent)
    prompt = render_prompt(agent, mode="confront", round=round_no, proposals=text, **variables)
    messages: list[BaseMessage] = [
        SystemMessage(prompt),
        HumanMessage(CONFRONT_REQUEST[round_no]),
        AIMessage(found.model_dump_json()),
        HumanMessage(problems_text(problems)),
    ]
    return await structured_call(
        model,
        Confrontation,
        messages,
        agent=agent,
        step=f"confrontation-{round_no}",
        intent="revising my positions",
    )


def _judged(round_no: int, agent: str, proposals: list[Proposal], contested: Any) -> list[Proposal]:
    if round_no == 1:
        return [p for p in proposals if author_of(p.ref) != agent]
    return [p for p in proposals if author_of(p.ref) == agent and p.ref in contested]


def make_confront(deps: GraphDeps, round_no: int) -> Node:
    @node_timeout(CONFRONT_TIMEOUT_S)
    async def confront(state: CvReviewState) -> CvReviewState:
        proposals = [Proposal.model_validate(p) for p in state.get("proposals", [])]
        contested = state.get("contested", {}) if round_no == 2 else {}
        if not proposals or (round_no == 2 and not contested):
            return {}
        _, _, variables = await review_inputs(deps, state)
        stances: dict[str, Stance] = {}
        for agent in AGENTS:
            judged = _judged(round_no, agent, proposals, contested)
            if not judged:
                continue
            mine = await ask_stances(deps, agent, round_no, variables, judged, contested)
            stances |= mine
            text = debate_text(round_no, agent, judged, mine, contested)
            message = {"message_id": f"{agent}-tour-{round_no}", "text": text}
            emit("agent.message", message, agent=agent)
        if round_no == 1:
            kept, found = apply_first(proposals, stances)
            out: CvReviewState = {"contested": found}
        else:
            kept, removed = apply_second(proposals, contested, stances)
            out = {"removed": removed}
        logger.info(
            "Confrontation : session %s, tour %d, %d proposition(s), %d position(s) non neutre(s)",
            deps.session_id,
            round_no,
            len(proposals),
            sum(s.stance != "keep" for s in stances.values()),
        )
        return {**out, "proposals": [p.model_dump(mode="json") for p in kept]}

    return confront

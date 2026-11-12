"""L'Éclaireur choisit les ressources d'un module (SPEC 3.6, D90) parmi les sources que la session
a lues et retenues (note 60 ou plus) : jamais une adresse écrite par le modèle. De 3 à 6 ; moins
si le web n'en a pas donné assez (signalé au rapport, jamais inventé).

Rien n'est écrit ici : le choix voyage dans l'état et le port l'enregistre à la publication."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import Field

from app.agents.nodes.lesson_common import LANGUAGES, Node, brief_of, kept_verdicts, module_prompt
from app.agents.nodes.scout.models import AGENT, one_line
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.lesson_factory import LessonFactoryState
from app.agents.tools.lesson_port import ResourcePick, ResourcePicks

MIN_RESOURCES = 3
MAX_RESOURCES = 6
ASKS = 2  # une demande, puis une re-demande si trop d'identifiants étaient inventés
RESOURCES_TIMEOUT_S = 240
INSUFFICIENT = "Ressources insuffisantes : {found} source(s) retenue(s) sur {wanted} attendues."

logger = logging.getLogger(__name__)


def _candidates_prompt(candidates: list[dict[str, Any]]) -> str:
    blocks = []
    for verdict in candidates:
        sid = verdict["source_id"]
        body = (
            f"Titre : {one_line(verdict['title'])}\nAdresse : {verdict['url']}\n"
            f"Langue : {verdict['lang'] or 'inconnue'}\nRésumé : {verdict['summary']}"
        )
        header = f"source_id : {sid} (note {verdict['score']}/100)"
        blocks.append(f"{header}\n{untrusted(body, f'ressource {sid}')}")
    return "\n\n".join(blocks)


def _valid(picks: ResourcePicks, allowed: set[str]) -> list[ResourcePick]:
    """Choix du modèle limités aux candidates, sans doublon : un identifiant inventé est retiré."""
    seen: set[str] = set()
    kept: list[ResourcePick] = []
    for pick in picks.resources:
        if pick.source_id in allowed and pick.source_id not in seen:
            seen.add(pick.source_id)
            kept.append(pick)
    return kept[:MAX_RESOURCES]


class _FewPicks(ResourcePicks):
    """Moins de 3 sources retenues : le web n'en a pas donné assez, on garde ce qu'il y a."""

    resources: list[ResourcePick] = Field(min_length=1, max_length=MAX_RESOURCES)


def make_pick_resources(deps: GraphDeps) -> Node:
    @node_timeout(RESOURCES_TIMEOUT_S)
    async def pick_resources(state: LessonFactoryState) -> LessonFactoryState:
        """3 sources retenues ou plus : le modèle choisit 3 à 6 ressources parmi elles, les
        identifiants hors candidates sont retirés. Moins de 3 : toutes les retenues sont
        décrites, avec la remarque « Ressources insuffisantes » (jamais une ressource inventée)."""
        candidates = kept_verdicts(state)
        enough = len(candidates) >= MIN_RESOURCES
        picks = await _ask(deps, state, candidates, ResourcePicks if enough else _FewPicks)
        notes = []
        if len(picks) < MIN_RESOURCES:
            notes.append(INSUFFICIENT.format(found=len(picks), wanted=MIN_RESOURCES))
            logger.info(
                "Ressources insuffisantes : session %s, %d retenue(s)", deps.session_id, len(picks)
            )
        return {"resources": [p.model_dump() for p in picks], "resource_notes": notes}

    return pick_resources


async def _ask(
    deps: GraphDeps,
    state: LessonFactoryState,
    candidates: list[dict[str, Any]],
    schema: type[ResourcePicks],
) -> list[ResourcePick]:
    if not candidates:
        return []
    brief = brief_of(state)
    wanted = min(MIN_RESOURCES, len(candidates))
    prompt = render_prompt(
        AGENT,
        mode="resources",
        module=module_prompt(brief),
        candidates=_candidates_prompt(candidates),
        min_resources=wanted,
        max_resources=min(MAX_RESOURCES, len(candidates)),
        language=LANGUAGES.get(brief.language, brief.language),
    )
    allowed = {v["source_id"] for v in candidates}
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage("Choisis les ressources.")]
    picks: list[ResourcePick] = []
    for ask in range(ASKS):
        found = await structured_call(
            model,
            schema,
            messages,
            agent=AGENT,
            step=f"ressources-{ask + 1}",
            intent="je choisis les ressources du module",
        )
        picks = _valid(found, allowed)
        if len(picks) >= wanted:
            break
        messages += [
            AIMessage(found.model_dump_json()),
            HumanMessage(
                "Certains source_id n'existent pas ou sont en double : choisis uniquement "
                "parmi ceux de la liste, sans doublon."
            ),
        ]
    return picks

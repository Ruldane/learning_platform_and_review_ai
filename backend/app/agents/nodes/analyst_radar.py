"""L'Analyste du radar du marché (P6, D159) : il lit les offres par lots de cinq (4 000 caractères
chacune, encadrées comme non fiables) et en tire compétences, outils, niveau et salaire. Le code
contrôle ce qu'il rend avant de le ranger : une référence inconnue est ignorée, un outil absent du
texte est retiré, un salaire dont les chiffres ne sont pas dans le texte est retiré. Un lot que le
modèle ne sait pas rendre valide (après les nouveaux essais de `structured_call`) marque ses pages
en échec d'extraction et la boucle continue. Une page absente de la réponse l'est de même : jamais
une page laissée sans issue, jamais une boucle sans fin.

La boucle relit `context` du port à chaque passage : une extraction déjà rangée n'est jamais
refaite après un redémarrage (SPEC 9.4). Au plus `MAX_READABLE` pages sont extraites (10 appels).

Journaux : identifiants et nombres seulement, jamais un lien, un site, un texte d'offre, un poste
ni une zone (17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.market_radar import MarketRadarState
from app.agents.tools.posting_schema import contains_term, normalize_term
from app.agents.tools.radar_port import MAX_READABLE, PostingPage
from app.agents.tools.radar_schema import (
    BATCH,
    TEXT_MAX,
    RadarBatch,
    RadarFinding,
    RadarItem,
    salary_in_text,
)
from app.core.errors import AppError

AGENT = "analyst"
RADAR_REQUEST = "Extrais ces offres du relevé du marché."  # les modèles scriptés s'y reconnaissent
INVALID_CODE = "structured_output_invalid"

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: MarketRadarState) -> MarketRadarState: ...


def local_ref(position: int) -> str:
    """Le repère d'une offre dans le lot : `p1` à `p5`."""
    return f"p{position}"


def radar_vars(batch: list[PostingPage]) -> dict[str, object]:
    """Variables du mode `radar` d'`analyst.md` : chaque page est un contenu non fiable (17.4),
    coupé à `TEXT_MAX` caractères."""
    pages = [
        untrusted(page.text[:TEXT_MAX], f"offre {local_ref(number)}")
        for number, page in enumerate(batch, start=1)
    ]
    return {"mode": "radar", "count": len(batch), "postings": "\n\n".join(pages)}


def _tools_in_text(tools: list[str], text: str) -> list[str]:
    """Les outils qui figurent dans `text` (mots entiers, sans casse ni accent), une fois chacun."""
    kept: list[str] = []
    seen: set[str] = set()
    for tool in tools:
        key = normalize_term(tool)
        if key and key not in seen and contains_term(text, tool):
            seen.add(key)
            kept.append(tool)
    return kept


def clean_item(item: RadarItem, page: PostingPage) -> RadarFinding:
    """L'extraction de `page`, contrôlée par le code et rangée sous le repère de la page. Pas une
    offre : rien d'autre n'est gardé. Une offre : les outils absents du texte lu et un salaire
    dont un chiffre n'y figure pas sont retirés (SPEC 1, 18.3)."""
    if not item.is_job_posting:
        return RadarFinding(ref=page.ref, is_job_posting=False)
    shown = page.text[:TEXT_MAX]
    tools = _tools_in_text(item.tools, shown)
    data = item.model_dump() | {
        "ref": page.ref,
        "tools": tools,
        "salary": salary_in_text(item.salary, shown),
    }
    return RadarFinding.model_validate(data)


def clean_batch(
    found: RadarBatch, batch: list[PostingPage]
) -> tuple[list[RadarFinding], list[str], int]:
    """`(offres rangées, repères en échec, réponses ignorées)`. Une référence inconnue du lot ou
    déjà donnée est ignorée ; une page que la réponse oublie est en échec d'extraction."""
    by_local = {local_ref(number): page for number, page in enumerate(batch, start=1)}
    kept: dict[str, RadarFinding] = {}
    ignored = 0
    for item in found.items:
        page = by_local.get(item.ref)
        if page is None or page.ref in kept:
            ignored += 1
            continue
        kept[page.ref] = clean_item(item, page)
    failed = [page.ref for page in batch if page.ref not in kept]
    return [kept[page.ref] for page in batch if page.ref in kept], failed, ignored


def pending_pages(read: list[PostingPage], extracted: frozenset[str]) -> list[PostingPage]:
    """Les pages lisibles à extraire : les `MAX_READABLE` premières lues, sans celles que le port
    dit déjà extraites (ou en échec)."""
    readable = [page for page in read if page.status == "ok"][:MAX_READABLE]
    return [page for page in readable if page.ref not in extracted]


async def _ask(deps: GraphDeps, batch: list[PostingPage]) -> RadarBatch | None:
    """Le lot demandé à l'Analyste ; `None` si sa réponse reste invalide après les nouveaux essais
    (les autres pannes remontent)."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **radar_vars(batch))
    try:
        return await structured_call(
            model,
            RadarBatch,
            [SystemMessage(prompt), HumanMessage(RADAR_REQUEST)],
            agent=AGENT,
            step="extraction",
            intent="je lis les offres du relevé",
        )
    except AppError as exc:
        if exc.code != INVALID_CODE:
            raise
        return None


def make_extract(deps: GraphDeps) -> Node:
    @node_timeout()
    async def extract(state: MarketRadarState) -> MarketRadarState:
        """Un lot de cinq offres lisibles non extraites : un appel, un rangement. `extract_done`
        quand ce lot était le dernier (calculé sur ce que le port vient de rendre)."""
        run_id = state["run_id"]
        ctx = await deps.ports.radar.context(deps.user_id, run_id)
        pending = pending_pages(ctx.read, ctx.extracted)
        if not pending:
            return {"extract_done": True}
        batch = pending[:BATCH]
        found = await _ask(deps, batch)
        items: list[RadarFinding] = []
        failed, ignored = [page.ref for page in batch], 0
        if found is not None:
            items, failed, ignored = clean_batch(found, batch)
        await deps.ports.radar.save_extraction(deps.user_id, deps.session_id, run_id, items, failed)
        logger.info(
            "Lot extrait : session %s, relevé %s, %d offre(s), %d en échec, %d ignorée(s)",
            deps.session_id,
            run_id,
            len(items),
            len(failed),
            ignored,
        )
        return {"extract_done": len(pending) <= len(batch)}

    return extract


def route_extract(state: MarketRadarState) -> str:
    return "finish" if state.get("extract_done") else "extract"

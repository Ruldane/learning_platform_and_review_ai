"""L'Éclaireur en mode `company` (SPEC 5.3, D129) : la fiche de l'entreprise d'une offre, pour la
revue du CV.

Entreprise inconnue → l'étape est sautée et dite dans le fil. Fiche de moins de 30 jours
(`ReviewContext.company_brief`) → reprise telle quelle, sans recherche ni écriture. Sinon :
`web_search` du nom de l'entreprise, trois pages lues au plus (`page_agent_text`, encadrées),
`CompanyBrief` demandée au modèle avec l'offre (encadrée), puis rangée (`save_company`, idempotent
par entreprise et session). L'ATS est reconnu au domaine des liens de l'offre (lien de
candidature compris) et des pages lues (`detect_ats`). Une recherche refusée (plafond, moteur
absent) ou une sortie du modèle invalide ne bloque pas la revue : elle continue sans fiche.

Journaux : identifiants et nombres, jamais le nom de l'entreprise ni une adresse (17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.scout.models import AGENT
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.ats_hosts import detect_ats
from app.agents.tools.cv_review_port import ReviewContext
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import CompanyBrief
from app.agents.tools.web_port import PageRead
from app.agents.tools.web_tools import page_agent_text, web_read, web_search
from app.core.errors import AppError

COMPANY_REQUEST = "Write the company dossier."
MAX_COMPANY_PAGES = 3
COMPANY_TIMEOUT_S = 300  # une recherche, trois pages (15 s chacune), une sortie structurée
MAX_POSTING_CHARS = 30_000
UNKNOWN = "The posting does not identify a company. Continuing with the CV review."
NO_BRIEF = "The company dossier could not be prepared. The CV review will continue."

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


async def _pages(deps: GraphDeps, name: str) -> list[PageRead]:
    """Les pages lisibles parmi les trois premiers résultats ; une erreur de recherche lève."""
    found = await web_search(deps, name, agent=AGENT)
    pages: list[PageRead] = []
    for hit in found.hits[:MAX_COMPANY_PAGES]:
        try:
            page = await web_read(deps, hit.url, agent=AGENT)
        except AppError:
            continue  # plafond de pages, adresse refusée : la page est sautée
        if page.status == "ok":
            pages.append(page)
    return pages


async def _brief(deps: GraphDeps, name: str, posting: str, pages: list[PageRead]) -> CompanyBrief:
    prompt = render_prompt(
        AGENT,
        mode="company",
        company=untrusted(name, "company"),
        posting=untrusted(posting[:MAX_POSTING_CHARS], "job posting"),
        pages="\n\n".join(page_agent_text(page) for page in pages) or "No pages read.",
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        CompanyBrief,
        [SystemMessage(prompt), HumanMessage(COMPANY_REQUEST)],
        agent=AGENT,
        step="fiche-entreprise",
        intent="Preparing the company dossier",
    )


def _links(ctx: ReviewContext, analysis: PostingAnalysis) -> list[str]:
    return [*ctx.posting_urls, *([analysis.apply_url] if analysis.apply_url else [])]


async def _research(
    deps: GraphDeps, ctx: ReviewContext, name: str, links: list[str]
) -> CvReviewState:
    """Recherche, fiche demandée au modèle, fiche rangée ; rien de rangé en cas d'échec."""
    try:
        pages = await _pages(deps, name)
        brief = await _brief(deps, name, ctx.posting_text, pages)
    except AppError as exc:
        logger.info("Fiche entreprise abandonnée : session %s, code %s", deps.session_id, exc.code)
        _say("fiche", NO_BRIEF)
        return {"company": name, "company_brief": None, "ats": detect_ats(links)}
    sources = [page.url for page in pages]
    ats = detect_ats([*links, *sources])
    await deps.ports.cv_review.save_company(
        deps.user_id, deps.session_id, name, brief, sources, ats
    )
    logger.info(
        "Fiche entreprise rangée : session %s, revue %s, %d page(s) lue(s), ATS repéré %s",
        deps.session_id,
        ctx.review_id,
        len(pages),
        ats is not None,
    )
    read_count = "1 page read" if len(pages) == 1 else f"{len(pages)} pages read"
    _say("fiche", f"The company dossier is ready ({read_count}).")
    return {"company": name, "company_brief": brief.model_dump(mode="json"), "ats": ats}


def make_company(deps: GraphDeps) -> Node:
    @node_timeout(COMPANY_TIMEOUT_S)
    async def company(state: CvReviewState) -> CvReviewState:
        ctx = await deps.ports.cv_review.context(deps.user_id, state["review_id"])
        analysis = PostingAnalysis.model_validate(state["analysis"])
        links = _links(ctx, analysis)
        name = ctx.company or analysis.company
        if not name:
            logger.info(
                "Entreprise inconnue : session %s, revue %s", deps.session_id, ctx.review_id
            )
            _say("fiche", UNKNOWN)
            return {"company": None, "company_brief": None, "ats": detect_ats(links)}
        if ctx.company_brief is not None:
            logger.info(
                "Fiche entreprise reprise : session %s, revue %s", deps.session_id, ctx.review_id
            )
            _say("fiche", "Using the recent company dossier for this review.")
            brief = ctx.company_brief.model_dump(mode="json")
            return {
                "company": name,
                "company_brief": brief,
                "ats": detect_ats(links) or ctx.company_ats,
            }
        return await _research(deps, ctx, name, links)

    return company

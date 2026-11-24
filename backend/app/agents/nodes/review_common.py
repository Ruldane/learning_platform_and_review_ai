"""Ce que partagent le Lecteur ATS et le Recruteur (parcours `cv_review`, D129) : le contexte rendu
au modèle (offre, analyse, fiche entreprise, indicateurs, profil et CV, **tous encadrés** par
`untrusted`, 17.4), la demande de propositions avec ses re-demandes, et le tri des propositions
valables.

Une proposition cite des identifiants de faits du profil (`x1a2`) : ceux qui manquent au profil,
une référence en double ou d'un autre agent sont renvoyés au modèle (`proposal_problems`), deux
fois au plus ; ensuite seules les propositions sans défaut sont gardées. Les phrases renvoyées ne
citent que des références et des identifiants, jamais un texte du CV."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.structured import structured_call
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.cv_indicators import Indicators
from app.agents.tools.cv_review_port import AtsUpdate, ReviewContext
from app.agents.tools.cv_schema import CvContent, MasterProfileData, facts_of, in_cv
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import CompanyBrief, Proposal, ProposalList, proposal_problems

PROPOSE_REQUEST = "Propose tes modifications du CV."
MAX_PROPOSE_ASKS = 3  # une demande, puis deux re-demandes avec les défauts
PROPOSE_TIMEOUT_S = 600  # sorties structurées longues (GLM) et leurs re-demandes
MAX_POSTING_CHARS = 30_000  # comme l'Analyste
MAX_UPDATE_CHARS = 500  # résumé d'une mise à jour ATS rendu au modèle
PREFIX = {"ats_reader": "a", "recruiter": "r"}
AGENT_OF = {prefix: agent for agent, prefix in PREFIX.items()}
LABEL = {"ats_reader": "ATS Reader", "recruiter": "Recruiter"}

logger = logging.getLogger(__name__)


def author_of(ref: str) -> str:
    """L'agent qui a écrit la proposition `ref` (`a…` : Lecteur ATS, `r…` : Recruteur)."""
    return AGENT_OF[ref[:1]]


def facts_text(profile: MasterProfileData) -> str:
    """Les faits du profil, un par ligne : identifiant, texte, et s'il est déjà dans le CV."""
    ids = in_cv(profile)
    return "\n".join(
        f"[{fact_id}] {text}" + ("" if fact_id in ids else " (hors du CV)")
        for fact_id, text in facts_of(profile).items()
    )


def cv_text(content: CvContent, profile: MasterProfileData) -> str:
    """Le CV d'origine, section par section, chaque ligne avec ses faits (sans coordonnées)."""
    out: list[str] = []
    title = profile.title
    if content.headline:
        cited = f"[{title.id}] " if title is not None and title.text == content.headline else ""
        out.append(f"Accroche : {cited}{content.headline}")
    for section in content.sections:
        out.append(f"## {section.title} ({section.key})")
        for entry in section.entries:
            head = " — ".join(p for p in (entry.heading, entry.subheading, entry.dates) if p)
            out.append(f"- [{entry.fact_id or '?'}] {head}")
            out += [f"  - [{', '.join(line.fact_ids)}] {line.text}" for line in entry.lines]
        out += [f"- [{', '.join(line.fact_ids)}] {line.text}" for line in section.items]
    return "\n".join(out)


def analysis_text(analysis: PostingAnalysis) -> str:
    lines = [f"Intitulé : {analysis.title}", f"Niveau : {analysis.level}"]
    lines += [
        f"Exigence ({'obligatoire' if r.required else 'souhaitée'}) : {r.text}"
        for r in analysis.requirements
    ]
    lines += [f"Mot clé : {k.term}" for k in analysis.keywords]
    lines += [f"Outil : {tool}" for tool in analysis.tools]
    lines += [f"Éliminatoire : {e.text}" for e in analysis.eliminatory]
    return "\n".join(lines)


def brief_text(brief: CompanyBrief | None) -> str:
    if brief is None:
        return "Aucune fiche entreprise."
    lines = [brief.summary]
    if brief.values:
        lines.append(f"Valeurs : {', '.join(brief.values)}")
    if brief.stack:
        lines.append(f"Outils : {', '.join(brief.stack)}")
    if brief.tone:
        lines.append(f"Ton : {brief.tone}")
    return untrusted("\n".join(lines), "fiche entreprise")


def indicators_text(before: Indicators) -> str:
    """Couverture des exigences obligatoires et contrôles ATS échoués (phrases du code) ; les
    exigences manquantes viennent de l'offre : encadrées."""
    cov = before.coverage
    lines = [f"Couverture des exigences obligatoires : {cov.covered}/{cov.total} ({cov.percent} %)"]
    if cov.missing:
        lines.append(untrusted("\n".join(cov.missing), "offre:exigences non couvertes"))
    failed = [check.detail for check in before.checks if not check.passed]
    lines += [f"Contrôle échoué : {detail}" for detail in failed] or ["Aucun contrôle échoué."]
    return "\n".join(lines)


def ats_updates_text(updates: list[AtsUpdate]) -> str:
    """Les mises à jour du web sur les ATS (P14) : titre, date, résumé, adresse, le tout encadré
    (17.4). Vide sans mise à jour : le prompt n'ajoute alors rien."""
    if not updates:
        return ""
    lines = []
    for update in updates:
        title = " ".join(update.title.split())
        summary = " ".join(update.summary.split())[:MAX_UPDATE_CHARS]
        lines.append(
            f"- {title} ({update.published or 'date inconnue'}) : {summary}\n  {update.url}"
        )
    return untrusted("\n".join(lines), "base ATS : mises à jour du web")


def context_vars(
    ctx: ReviewContext, analysis: PostingAnalysis, brief: CompanyBrief | None, ats: str | None
) -> dict[str, Any]:
    """Les variables communes des prompts ; tout ce qui vient de l'offre, du web, du CV ou du
    profil est encadré (17.4)."""
    return {
        "ats": ats or "inconnu",
        "posting": untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "offre"),
        "analysis": untrusted(analysis_text(analysis), "offre:analyse"),
        "brief": brief_text(brief),
        "indicators": indicators_text(ctx.before),
        "profile": untrusted(facts_text(ctx.profile), "profil"),
        "cv": untrusted(cv_text(ctx.base, ctx.profile), "cv"),
        "ats_updates": ats_updates_text(ctx.ats_updates),
    }


def proposal_issues(items: list[Proposal], profile: MasterProfileData, prefix: str) -> list[str]:
    """Défauts renvoyés au modèle : ceux de `proposal_problems`, plus une référence qui ne
    commence pas par la lettre de l'agent."""
    wrong = [
        f"La référence {p.ref} n'est pas à toi : tes références commencent par « {prefix} »."
        for p in items
        if not p.ref.startswith(prefix)
    ]
    return wrong + proposal_problems(items, profile)


def keep_valid(items: list[Proposal], profile: MasterProfileData, prefix: str) -> list[Proposal]:
    """Les propositions sans défaut, la première d'une référence en double."""
    kept: list[Proposal] = []
    seen: set[str] = set()
    for p in items:
        if p.ref in seen or proposal_issues([p], profile, prefix):
            continue
        seen.add(p.ref)
        kept.append(p)
    return kept


def problems_text(problems: list[str]) -> str:
    return (
        "Ta réponse a ces défauts :\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + "\nCorrige-les et rends de nouveau toutes tes propositions."
    )


async def ask_proposals[T: ProposalList](
    deps: GraphDeps,
    agent: str,
    schema: type[T],
    variables: dict[str, Any],
    profile: MasterProfileData,
) -> tuple[T, list[Proposal]]:
    """Une demande, puis deux re-demandes au plus avec les défauts ; rend la dernière réponse et
    ses propositions valables."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(agent).tier, agent=agent)
    prefix = PREFIX[agent]
    prompt = render_prompt(agent, mode="propose", prefix=prefix, **variables)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(PROPOSE_REQUEST)]
    for ask in range(1, MAX_PROPOSE_ASKS + 1):
        found = await structured_call(
            model,
            schema,
            messages,
            agent=agent,
            step=f"propositions-{ask}",
            intent="reviewing your CV for the posting" if ask == 1 else "revising my suggestions",
        )
        problems = proposal_issues(found.items, profile, prefix)
        if not problems or ask == MAX_PROPOSE_ASKS:
            break
        logger.info(
            "Propositions redemandées : session %s, agent %s, %d défaut(s)",
            deps.session_id,
            agent,
            len(problems),
        )
        messages += [AIMessage(found.model_dump_json()), HumanMessage(problems_text(problems))]
    kept = keep_valid(found.items, profile, prefix)
    logger.info(
        "Propositions : session %s, agent %s, %d reçue(s), %d gardée(s)",
        deps.session_id,
        agent,
        len(found.items),
        len(kept),
    )
    return found, kept


async def review_inputs(
    deps: GraphDeps, state: CvReviewState
) -> tuple[ReviewContext, PostingAnalysis, dict[str, Any]]:
    """Le contexte relu par le port (lecture seule), l'analyse de l'état et les variables
    communes des prompts."""
    ctx = await deps.ports.cv_review.context(deps.user_id, state["review_id"])
    assert state.get("analysis") is not None  # garanti par `load` ou `save_analysis`
    analysis = PostingAnalysis.model_validate(state["analysis"])
    raw = state.get("company_brief")
    brief = CompanyBrief.model_validate(raw) if raw else None
    return ctx, analysis, context_vars(ctx, analysis, brief, state.get("ats"))

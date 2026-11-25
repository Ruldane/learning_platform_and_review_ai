"""What the ATS Reader and the Recruiter share (flow `cv_review`, D129): the context given to
the model (posting, analysis, company sheet, indicators, profile and CV, **all wrapped** by
`untrusted`, 17.4), the request for proposals with its re-requests, and the sorting of the valid
proposals.

A proposal cites ids of profile facts (`x1a2`): those missing from the profile, a duplicate
reference or one of another agent are sent back to the model (`proposal_problems`), twice at
most; after that only the proposals without defects are kept. The sentences sent back only
cite references and identifiers, never a text of the CV."""

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

PROPOSE_REQUEST = "Propose your changes to the CV."
MAX_PROPOSE_ASKS = 3  # one request, then two re-requests with the defects
PROPOSE_TIMEOUT_S = 600  # long structured outputs (GLM) and their re-requests
MAX_POSTING_CHARS = 30_000  # like the Analyst
MAX_UPDATE_CHARS = 500  # summary of an ATS update handed to the model
PREFIX = {"ats_reader": "a", "recruiter": "r"}
AGENT_OF = {prefix: agent for agent, prefix in PREFIX.items()}
LABEL = {"ats_reader": "ATS Reader", "recruiter": "Recruiter"}

logger = logging.getLogger(__name__)


def author_of(ref: str) -> str:
    """The agent that wrote proposal `ref` (`a...`: ATS Reader, `r...`: Recruiter)."""
    return AGENT_OF[ref[:1]]


def facts_text(profile: MasterProfileData) -> str:
    """The profile facts, one per line: identifier, text, and whether it is already in the CV."""
    ids = in_cv(profile)
    return "\n".join(
        f"[{fact_id}] {text}" + ("" if fact_id in ids else " (not in the CV)")
        for fact_id, text in facts_of(profile).items()
    )


def cv_text(content: CvContent, profile: MasterProfileData) -> str:
    """The original CV, section by section, each line with its facts (without contact details)."""
    out: list[str] = []
    title = profile.title
    if content.headline:
        cited = f"[{title.id}] " if title is not None and title.text == content.headline else ""
        out.append(f"Headline: {cited}{content.headline}")
    for section in content.sections:
        out.append(f"## {section.title} ({section.key})")
        for entry in section.entries:
            head = " — ".join(p for p in (entry.heading, entry.subheading, entry.dates) if p)
            out.append(f"- [{entry.fact_id or '?'}] {head}")
            out += [f"  - [{', '.join(line.fact_ids)}] {line.text}" for line in entry.lines]
        out += [f"- [{', '.join(line.fact_ids)}] {line.text}" for line in section.items]
    return "\n".join(out)


def analysis_text(analysis: PostingAnalysis) -> str:
    lines = [f"Title: {analysis.title}", f"Level: {analysis.level}"]
    lines += [
        f"Requirement ({'mandatory' if r.required else 'preferred'}): {r.text}"
        for r in analysis.requirements
    ]
    lines += [f"Keyword: {k.term}" for k in analysis.keywords]
    lines += [f"Tool: {tool}" for tool in analysis.tools]
    lines += [f"Knockout: {e.text}" for e in analysis.eliminatory]
    return "\n".join(lines)


def brief_text(brief: CompanyBrief | None) -> str:
    if brief is None:
        return "No company sheet."
    lines = [brief.summary]
    if brief.values:
        lines.append(f"Values: {', '.join(brief.values)}")
    if brief.stack:
        lines.append(f"Tools: {', '.join(brief.stack)}")
    if brief.tone:
        lines.append(f"Tone: {brief.tone}")
    return untrusted("\n".join(lines), "company sheet")


def indicators_text(before: Indicators) -> str:
    """Coverage of the mandatory requirements and failed ATS checks (sentences of the code); the
    missing requirements come from the posting: wrapped."""
    cov = before.coverage
    lines = [f"Coverage of the mandatory requirements: {cov.covered}/{cov.total} ({cov.percent}%)"]
    if cov.missing:
        lines.append(untrusted("\n".join(cov.missing), "posting:uncovered requirements"))
    failed = [check.detail for check in before.checks if not check.passed]
    lines += [f"Failed check: {detail}" for detail in failed] or ["No failed check."]
    return "\n".join(lines)


def ats_updates_text(updates: list[AtsUpdate]) -> str:
    """The web updates about ATS (P14): title, date, summary, address, all wrapped
    (17.4). Empty without an update: the prompt then adds nothing."""
    if not updates:
        return ""
    lines = []
    for update in updates:
        title = " ".join(update.title.split())
        summary = " ".join(update.summary.split())[:MAX_UPDATE_CHARS]
        lines.append(f"- {title} ({update.published or 'date unknown'}): {summary}\n  {update.url}")
    return untrusted("\n".join(lines), "ATS base: web updates")


def context_vars(
    ctx: ReviewContext, analysis: PostingAnalysis, brief: CompanyBrief | None, ats: str | None
) -> dict[str, Any]:
    """The common prompt variables; everything that comes from the posting, the web, the CV or
    the profile is wrapped (17.4)."""
    return {
        "ats": ats or "unknown",
        "posting": untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "posting"),
        "analysis": untrusted(analysis_text(analysis), "posting:analysis"),
        "brief": brief_text(brief),
        "indicators": indicators_text(ctx.before),
        "profile": untrusted(facts_text(ctx.profile), "profile"),
        "cv": untrusted(cv_text(ctx.base, ctx.profile), "cv"),
        "ats_updates": ats_updates_text(ctx.ats_updates),
    }


def proposal_issues(items: list[Proposal], profile: MasterProfileData, prefix: str) -> list[str]:
    """Defects sent back to the model: those of `proposal_problems`, plus a reference that does
    not start with the agent's letter."""
    wrong = [
        f'Reference {p.ref} is not yours: your references start with "{prefix}".'
        for p in items
        if not p.ref.startswith(prefix)
    ]
    return wrong + proposal_problems(items, profile)


def keep_valid(items: list[Proposal], profile: MasterProfileData, prefix: str) -> list[Proposal]:
    """The proposals without defects, the first one of a duplicated reference."""
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
        "Your answer has these defects:\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + "\nFix them and return all your proposals again."
    )


async def ask_proposals[T: ProposalList](
    deps: GraphDeps,
    agent: str,
    schema: type[T],
    variables: dict[str, Any],
    profile: MasterProfileData,
) -> tuple[T, list[Proposal]]:
    """One request, then two re-requests at most with the defects; returns the last answer and
    its valid proposals."""
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
            "Proposals requested again: session %s, agent %s, %d defect(s)",
            deps.session_id,
            agent,
            len(problems),
        )
        messages += [AIMessage(found.model_dump_json()), HumanMessage(problems_text(problems))]
    kept = keep_valid(found.items, profile, prefix)
    logger.info(
        "Proposals: session %s, agent %s, %d received, %d kept",
        deps.session_id,
        agent,
        len(found.items),
        len(kept),
    )
    return found, kept


async def review_inputs(
    deps: GraphDeps, state: CvReviewState
) -> tuple[ReviewContext, PostingAnalysis, dict[str, Any]]:
    """The context reread by the port (read-only), the state's analysis and the common prompt
    variables."""
    ctx = await deps.ports.cv_review.context(deps.user_id, state["review_id"])
    assert state.get("analysis") is not None  # guaranteed by `load` or `save_analysis`
    analysis = PostingAnalysis.model_validate(state["analysis"])
    raw = state.get("company_brief")
    brief = CompanyBrief.model_validate(raw) if raw else None
    return ctx, analysis, context_vars(ctx, analysis, brief, state.get("ats"))

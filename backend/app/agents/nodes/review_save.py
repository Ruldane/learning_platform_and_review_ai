"""Validation and filing of the review proposals (SPEC 5.5, 18.3, D128, D129).

`validate` runs each proposal left after the confrontation through the code validator
(`cv_validator.validate`, against the master profile frozen in the review): `ok` and
`to_confirm` become changes, `to_gap` is removed and its terms go to the gap (a posting keyword
that the cited facts do not support never enters the CV). `save` files everything with the
report (`save_proposals`, idempotent per `(review, reference)`) then announces it.

Logs: identifiers and numbers, never a CV text or a posting term (17.2)."""

import logging
from typing import Protocol

from app.agents.nodes.review_common import review_inputs
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.cv_review import CvReviewState
from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.cv_validator import Verdict, validate
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_notes import without_promises
from app.agents.tools.review_schema import CompanyBrief, Proposal

AGENT = "recruiter"  # the voice that announces the result of the review
SAVE_TIMEOUT_S = 300

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def judge(
    proposals: list[Proposal], profile: MasterProfileData, analysis: PostingAnalysis
) -> tuple[list[tuple[Proposal, Verdict]], list[str]]:
    """`(kept proposals with their verdict, terms that went to the gap)`, order kept."""
    kept: list[tuple[Proposal, Verdict]] = []
    gap: dict[str, str] = {}
    for p in proposals:
        verdict = validate(p, profile, analysis)
        if verdict.status == "to_gap":
            for term in verdict.gap_terms:
                gap.setdefault(term.casefold(), term)
            continue
        kept.append((p, verdict))
    return kept, list(gap.values())


def make_validate(deps: GraphDeps) -> Node:
    @node_timeout()
    async def validate_all(state: CvReviewState) -> CvReviewState:
        ctx, analysis, _ = await review_inputs(deps, state)
        proposals = [Proposal.model_validate(p) for p in state.get("proposals", [])]
        kept, gap_terms = judge(proposals, ctx.profile, analysis)
        logger.info(
            "Proposals validated: session %s, review %s, %d kept, %d to confirm, "
            "%d to the gap, %d term(s)",
            deps.session_id,
            state["review_id"],
            len(kept),
            sum(v.status == "to_confirm" for _, v in kept),
            len(proposals) - len(kept),
            len(gap_terms),
        )
        items = [
            {"proposal": p.model_dump(mode="json"), "status": v.status, "blocks": v.blocks}
            for p, v in kept
        ]
        return {"items": items, "gap_terms": gap_terms}

    return validate_all


def report_of(state: CvReviewState, analysis: PostingAnalysis) -> ReviewReport:
    raw = state.get("company_brief")
    brief = CompanyBrief.model_validate(raw) if raw else None
    return ReviewReport(
        ats=state.get("ats"),
        ats_notes=without_promises(state.get("ats_notes", []))[:6],
        company_summary=brief.summary if brief else None,
        strengths=without_promises(state.get("strengths", []))[:5],
        risks=without_promises(state.get("risks", []))[:5],
        eliminatory=[e.text for e in analysis.eliminatory][:10],
    )


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def saved_text(proposed: int, to_confirm: int, gap: int) -> str:
    """Example: 9 changes proposed, 2 to confirm. 1 posting keyword moves to the gap."""
    text = f"{_plural(proposed, 'change', 'changes')} proposed, "
    text += f"{to_confirm} to confirm."
    if gap:
        moves = "moves" if gap == 1 else "move"
        text += f" {_plural(gap, 'posting keyword', 'posting keywords')} {moves} to the gap."
    return text


def make_save(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save(state: CvReviewState) -> CvReviewState:
        """Idempotent: replayed, the port rereads the changes already filed."""
        analysis = PostingAnalysis.model_validate(state["analysis"])
        items = [
            (
                Proposal.model_validate(item["proposal"]),
                Verdict(item["status"], list(item["blocks"]), []),
            )
            for item in state.get("items", [])
        ]
        gap_terms = state.get("gap_terms", [])
        saved = await deps.ports.cv_review.save_proposals(
            deps.user_id,
            deps.session_id,
            state["review_id"],
            items,
            gap_terms,
            report_of(state, analysis),
        )
        to_confirm = sum(v.status == "to_confirm" for _, v in items)
        logger.info(
            "Review stored: session %s, review %s, %d change(s), %d to confirm",
            deps.session_id,
            state["review_id"],
            saved,
            to_confirm,
        )
        text = saved_text(len(items), to_confirm, len(gap_terms))
        emit("agent.message", {"message_id": f"{AGENT}-revue", "text": text}, agent=AGENT)
        return {"saved": saved, "summary": text}

    return save

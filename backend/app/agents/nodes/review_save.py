"""Validation et rangement des propositions de la revue (SPEC 5.5, 18.3, D128, D129).

`validate` passe chaque proposition restée après la confrontation au validateur du code
(`cv_validator.validate`, contre le profil maître figé dans la revue) : `ok` et `to_confirm`
deviennent des modifications, `to_gap` est retirée et ses termes partent vers l'écart (un mot clé
de l'offre que les faits cités ne portent pas n'entre jamais dans le CV). `save` range le tout
avec le rapport (`save_proposals`, idempotent par `(revue, référence)`) puis l'annonce.

Journaux : identifiants et nombres, jamais un texte du CV ni un terme de l'offre (17.2)."""

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

AGENT = "recruiter"  # la voix qui annonce le résultat de la revue
SAVE_TIMEOUT_S = 300

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


def judge(
    proposals: list[Proposal], profile: MasterProfileData, analysis: PostingAnalysis
) -> tuple[list[tuple[Proposal, Verdict]], list[str]]:
    """`(propositions gardées avec leur verdict, termes partis vers l'écart)`, ordre gardé."""
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
            "Propositions validées : session %s, revue %s, %d gardée(s), %d à confirmer, "
            "%d vers l'écart, %d terme(s)",
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
    """« 9 modifications proposées, 2 à confirmer. 1 mot clé de l'offre part vers l'écart. »"""
    text = f"{_plural(proposed, 'modification proposée', 'modifications proposées')}, "
    text += f"{to_confirm} à confirmer."
    if gap:
        moves = "part" if gap == 1 else "partent"
        text += f" {_plural(gap, 'mot clé', 'mots clés')} de l'offre {moves} vers l'écart."
    return text


def make_save(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save(state: CvReviewState) -> CvReviewState:
        """Idempotent : rejoué, le port relit les modifications déjà rangées."""
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
            "Revue rangée : session %s, revue %s, %d modification(s), %d à confirmer",
            deps.session_id,
            state["review_id"],
            saved,
            to_confirm,
        )
        text = saved_text(len(items), to_confirm, len(gap_terms))
        emit("agent.message", {"message_id": f"{AGENT}-revue", "text": text}, agent=AGENT)
        return {"saved": saved, "summary": text}

    return save

"""What the committee personas read (D147): the CV and the posting (always wrapped by
`untrusted`, 17.4), the company dossier from the debate on, the posting terms seen in the CV
(ATS Reader) and everything the others said (agent output: wrapped too). A missing piece is
said to be missing, never invented.

At the first impression, a persona only sees the CV and the posting (SPEC F19): the dossier only
comes in afterwards; the company size, however, sets the tone from the start
(`_shared/committee.md`)."""

from collections.abc import Sequence
from typing import Any

from app.agents.nodes.interviewer.context import dossier_lines
from app.agents.nodes.review_common import analysis_text
from app.agents.prompts.loader import untrusted
from app.agents.tools.committee_schema import LABELS, MAX_WORDS, CommitteeContext, Persona

MAX_POSTING_CHARS = 12_000
NO_DOSSIER = "No company dossier is available."
NO_SPEECH = "The discussion has yet to start."
STEP_LABELS = {0: "first impression", 1: "round 1", 2: "round 2"}


def dossier_block(ctx: CommitteeContext) -> str:
    if ctx.dossier is None:
        return NO_DOSSIER
    return untrusted("\n".join(dossier_lines(ctx.dossier)), "company dossier")


def ats_terms_block(ctx: CommitteeContext) -> str:
    """The posting terms the CV does or does not write (they come from the posting: wrapped)."""
    found = ", ".join(ctx.ats_terms.found) or "none"
    missing = ", ".join(ctx.ats_terms.missing) or "none"
    lines = [f"Posting terms found in the CV: {found}", f"Missing from the CV: {missing}"]
    return untrusted("\n".join(lines), "posting terms")


def transcript_text(spoken: Sequence[dict[str, Any]]) -> str:
    """Everything that was said, in order: each speech wrapped (output of another agent)."""
    if not spoken:
        return NO_SPEECH
    return "\n\n".join(
        f"{LABELS[item['persona']]}, {STEP_LABELS[item['round']]}:\n"
        + untrusted(item["text"], f"{item['persona']} {STEP_LABELS[item['round']]}")
        for item in spoken
    )


def persona_vars(
    ctx: CommitteeContext,
    persona: Persona,
    step: str,
    spoken: Sequence[dict[str, Any]] = (),
    round_number: int = 0,
    addressee: Persona | None = None,
) -> dict[str, Any]:
    """The prompt variables of a persona (`committee` mode) for step `step`."""
    return {
        "mode": "committee",
        "persona": persona,
        "step": step,
        "persona_name": LABELS[persona],
        "size": ctx.size,
        "cv": untrusted(ctx.cv_text, "cv"),
        "posting": untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "job posting"),
        "analysis": untrusted(analysis_text(ctx.analysis), "posting analysis"),
        "dossier": "" if step == "impression" else dossier_block(ctx),
        "ats_terms": ats_terms_block(ctx),
        "transcript": transcript_text(spoken),
        "round": round_number,
        "addressee": LABELS[addressee] if addressee else None,
        "others": ", ".join(label for slug, label in LABELS.items() if slug != persona),
        "max_words": MAX_WORDS,
    }

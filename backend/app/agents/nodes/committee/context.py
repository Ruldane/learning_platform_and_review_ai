"""Ce que les personas du comité lisent (D147) : le CV et l'offre (toujours encadrés par
`untrusted`, 17.4), le dossier de l'entreprise à partir du débat, les termes de l'offre vus dans
le CV (Lecteur ATS) et tout ce que les autres ont dit (sortie d'un agent : encadrée aussi). Un
morceau absent est dit absent, jamais inventé.

À la première impression, une persona ne voit que le CV et l'offre (SPEC F19) : le dossier n'entre
qu'ensuite ; la taille de l'entreprise, elle, règle le ton dès le début (`_shared/committee.md`)."""

from collections.abc import Sequence
from typing import Any

from app.agents.nodes.interviewer.context import dossier_lines
from app.agents.nodes.review_common import analysis_text
from app.agents.prompts.loader import untrusted
from app.agents.tools.committee_schema import LABELS, MAX_WORDS, CommitteeContext, Persona

MAX_POSTING_CHARS = 12_000
NO_DOSSIER = "Aucun dossier sur l'entreprise."
NO_SPEECH = "Personne n'a encore parlé."
STEP_LABELS = {0: "première impression", 1: "tour 1", 2: "tour 2"}


def dossier_block(ctx: CommitteeContext) -> str:
    if ctx.dossier is None:
        return NO_DOSSIER
    return untrusted("\n".join(dossier_lines(ctx.dossier)), "dossier de l'entreprise")


def ats_terms_block(ctx: CommitteeContext) -> str:
    """Les termes de l'offre que le CV écrit ou n'écrit pas (ils viennent de l'offre : encadrés)."""
    found = ", ".join(ctx.ats_terms.found) or "aucun"
    missing = ", ".join(ctx.ats_terms.missing) or "aucun"
    lines = [f"Termes de l'offre écrits dans le CV : {found}", f"Absents du CV : {missing}"]
    return untrusted("\n".join(lines), "offre:termes")


def transcript_text(spoken: Sequence[dict[str, Any]]) -> str:
    """Tout ce qui s'est dit, dans l'ordre : chaque parole encadrée (sortie d'un autre agent)."""
    if not spoken:
        return NO_SPEECH
    return "\n\n".join(
        f"{LABELS[item['persona']]}, {STEP_LABELS[item['round']]} :\n"
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
    """Les variables du prompt d'une persona (mode `committee`) pour l'étape `step`."""
    return {
        "mode": "committee",
        "persona": persona,
        "step": step,
        "persona_name": LABELS[persona],
        "size": ctx.size,
        "cv": untrusted(ctx.cv_text, "cv"),
        "posting": untrusted(ctx.posting_text[:MAX_POSTING_CHARS], "offre"),
        "analysis": untrusted(analysis_text(ctx.analysis), "offre:analyse"),
        "dossier": "" if step == "impression" else dossier_block(ctx),
        "ats_terms": ats_terms_block(ctx),
        "transcript": transcript_text(spoken),
        "round": round_number,
        "addressee": LABELS[addressee] if addressee else None,
        "others": ", ".join(label for slug, label in LABELS.items() if slug != persona),
        "max_words": MAX_WORDS,
    }

"""The committee synthesis (SPEC F19, D147): the Moderator ranks the objections (six at most)
and writes the three changes that would tip a vote; it takes no position on the substance.
The verdict is the majority of the four votes, **computed by the code** (`majority_verdict`,
SPEC F19: a tie or no majority, "maybe"): the model receives it, it does not choose it.

The code rereads what the model writes: an unknown persona is refused by the schema (`Literal`)
and sent back to the model; the personas of an objection are put back in the committee's order,
without duplicates; fact identifiers unknown to the profile are removed, and a change that asks
for a term the profile does not state becomes a skill "to acquire" (`committee_changes`),
never an "add X". `allowed` only contains the company and the exact job title.

Logs: identifiers, verdict and numbers only (17.2)."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.committee.common import SYNTHESIS_REQUEST, Node, context_of
from app.agents.nodes.committee.context import dossier_block, transcript_text
from app.agents.nodes.review_common import facts_text
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import (
    LABELS,
    PERSONAS,
    CommitteeContext,
    PersonaVote,
    RankedObjection,
    Synthesis,
    SynthesisDraft,
    committee_changes,
    majority_verdict,
)

AGENT = "moderator"
SYNTHESIS_TIMEOUT_S = 180

logger = logging.getLogger(__name__)


def allowed_phrases(ctx: CommitteeContext) -> list[str]:
    """The whole phrases that a change may write: the company and the job title,
    never a tool or a figure from the posting."""
    names = [ctx.company or "", ctx.title, ctx.analysis.company or "", ctx.analysis.title]
    return list(dict.fromkeys(name for name in names if name))


def votes_text(votes: list[PersonaVote]) -> str:
    """The votes as the Moderator reads them (the objection and the reason come from an agent)."""
    return "\n\n".join(
        f"{LABELS[v.persona]} ({v.persona}): {v.vote}\n"
        + untrusted(f"Objection: {v.objection}\nReason: {v.reason}", f"vote {v.persona}")
        for v in votes
    )


def known_personas(objections: list[RankedObjection]) -> list[RankedObjection]:
    """The personas of an objection, in the committee's order, without duplicates (an unknown
    persona is already refused by the schema)."""
    return [
        RankedObjection(text=o.text, personas=[p for p in PERSONAS if p in o.personas])
        for o in objections
    ]


def synthesis_text(synthesis: Synthesis) -> str:
    lines = [f"The committee voted {synthesis.verdict}.", "", "Objections"]
    lines += [f"{rank}. {o.text}" for rank, o in enumerate(synthesis.objections, start=1)]
    lines += ["", "Three changes that could change a vote"]
    lines += [f"- {LABELS[c.persona]} · {c.text}" for c in synthesis.changes]
    return "\n".join(lines)


def make_synthesis(deps: GraphDeps) -> Node:
    @node_timeout(SYNTHESIS_TIMEOUT_S)
    async def synthesis(state: HiringCommitteeState) -> HiringCommitteeState:
        ctx = context_of(state)
        votes = [PersonaVote.model_validate(v) for v in state["votes"]]
        verdict = majority_verdict(votes)
        prompt = render_prompt(
            AGENT,
            mode="committee",
            verdict=verdict,
            votes=votes_text(votes),
            transcript=transcript_text(state["spoken"]),
            dossier=dossier_block(ctx),
            facts=untrusted(facts_text(ctx.profile), "profile"),
            personas=", ".join(f"{slug} ({label})" for slug, label in LABELS.items()),
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        draft = await structured_call(
            model,
            SynthesisDraft,
            [SystemMessage(prompt), HumanMessage(SYNTHESIS_REQUEST)],
            agent=AGENT,
            step="synthese",
            intent="Summarizing the committee's discussion",
        )
        result = Synthesis(
            verdict=verdict,
            objections=known_personas(draft.objections),
            changes=committee_changes(draft.changes, ctx.profile, allowed_phrases(ctx)),
        )
        logger.info(
            "Synthesis written: session %s, verdict %s, %d objection(s), %d to acquire",
            deps.session_id,
            verdict,
            len(result.objections),
            sum(c.needs_skill for c in result.changes),
        )
        emit(
            "agent.message",
            {"message_id": f"{AGENT}-synthese", "text": synthesis_text(result)},
            agent=AGENT,
        )
        return {"synthesis": result.model_dump(mode="json")}

    return synthesis

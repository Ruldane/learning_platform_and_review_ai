"""La synthèse du comité (SPEC F19, D147) : le Modérateur classe les objections (six au plus) et
écrit les trois changements qui feraient basculer un vote ; il ne prend pas position sur le fond.
Le verdict, lui, est la majorité des quatre votes, **calculée par le code** (`majority_verdict`,
SPEC F19 : égalité ou aucune majorité, « peut-être ») : le modèle le reçoit, il ne le choisit pas.

Le code relit ce que le modèle écrit : une persona inconnue est refusée par le schéma (`Literal`)
et renvoyée au modèle ; les personas d'une objection sont remises dans l'ordre du comité, sans
doublon ; les identifiants de faits inconnus du profil sont retirés, et un changement qui demande
un terme que le profil ne dit pas devient une compétence « à acquérir » (`committee_changes`),
jamais un « ajoute X ». `allowed` ne contient que l'entreprise et l'intitulé exact du poste.

Journaux : identifiants, verdict et nombres seulement (17.2)."""

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
    VERDICT_WORDS,
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
    """Les expressions entières qu'un changement peut écrire : l'entreprise et l'intitulé du poste,
    jamais un outil ni un chiffre de l'offre."""
    names = [ctx.company or "", ctx.title, ctx.analysis.company or "", ctx.analysis.title]
    return list(dict.fromkeys(name for name in names if name))


def votes_text(votes: list[PersonaVote]) -> str:
    """Les votes tels que le Modérateur les lit (l'objection et la raison viennent d'un agent)."""
    return "\n\n".join(
        f"{LABELS[v.persona]} ({v.persona}) : {v.vote}\n"
        + untrusted(f"Objection : {v.objection}\nRaison : {v.reason}", f"vote {v.persona}")
        for v in votes
    )


def known_personas(objections: list[RankedObjection]) -> list[RankedObjection]:
    """Les personas d'une objection, dans l'ordre du comité, sans doublon (une persona inconnue est
    déjà refusée par le schéma)."""
    return [
        RankedObjection(text=o.text, personas=[p for p in PERSONAS if p in o.personas])
        for o in objections
    ]


def synthesis_text(synthesis: Synthesis) -> str:
    lines = [f"Verdict du comité : {VERDICT_WORDS[synthesis.verdict]}.", "", "Objections :"]
    lines += [f"{rank}. {o.text}" for rank, o in enumerate(synthesis.objections, start=1)]
    lines += ["", "Les trois changements qui feraient basculer un vote :"]
    lines += [f"- {LABELS[c.persona]} : {c.text}" for c in synthesis.changes]
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
            verdict=VERDICT_WORDS[verdict],
            votes=votes_text(votes),
            transcript=transcript_text(state["spoken"]),
            dossier=dossier_block(ctx),
            facts=untrusted(facts_text(ctx.profile), "profil"),
            personas=", ".join(f"{slug} ({label})" for slug, label in LABELS.items()),
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        draft = await structured_call(
            model,
            SynthesisDraft,
            [SystemMessage(prompt), HumanMessage(SYNTHESIS_REQUEST)],
            agent=AGENT,
            step="synthese",
            intent="je fais la synthèse du comité",
        )
        result = Synthesis(
            verdict=verdict,
            objections=known_personas(draft.objections),
            changes=committee_changes(draft.changes, ctx.profile, allowed_phrases(ctx)),
        )
        logger.info(
            "Synthèse écrite : session %s, verdict %s, %d objection(s), %d à acquérir",
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

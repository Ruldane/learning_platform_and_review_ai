"""L'Analyste (SPEC 5.3 étape 1, F8, D121) : il analyse une offre d'emploi et rattache ses
compétences au référentiel de January. Parcours `gap_analysis`.

`load` lit l'offre par le port ; une offre déjà analysée (par une autre session ou une revue de
CV) n'est jamais réanalysée. `analyze` refuse sans appel un texte trop court (`enough_text`, même
borne que la route), demande l'analyse (texte de l'offre encadré par `untrusted`), la fait
vérifier (mots clés tels quels dans l'offre, exigences obligatoires reliées à `skills`) et la
redemande deux fois au plus, en gardant la meilleure réponse ; les mots clés encore absents sont
retirés. Un texte qui n'est pas une offre est refusé (`reject`). `match` demande le rattachement
des besoins au référentiel existant, par identifiants ; le code calcule ensuite les lignes et le
score, puis ajoute au référentiel les besoins restés sans rattachement (`save_gap`).

Aucun point d'arrêt. Les écritures du port (`save_analysis`, `reject`, `save_gap`) sont
idempotentes : un nœud rejoué après un arrêt (SPEC 9.4) n'écrit rien de plus.

Journaux : identifiants et nombres seulement, jamais le texte de l'offre, un nom de compétence,
un titre ni une entreprise (17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.analyst_steps import (
    AGENT,
    ANALYZE_REQUEST,
    MATCH_REQUEST,
    MAX_ANALYZE_ASKS,
    MAX_POSTING_CHARS,
    NOT_A_POSTING,
    TOO_SHORT,
    Problem,
    analysis_problems,
    analyze_vars,
    better_answer,
    clean_matches,
    drop_absent_keywords,
    duplicate_text,
    duplicates_json,
    gap_text,
    match_vars,
    problems_text,
    saved_json,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.gap_analysis import GapAnalysisState
from app.agents.tools.gap_port import GapSaved, KnownSkill, SkillMatch, SkillMatches
from app.agents.tools.posting_schema import PostingAnalysis, enough_text

ANALYZE_TIMEOUT_S = 600  # trois demandes d'une analyse longue (GLM), avec leurs nouveaux essais
MATCH_TIMEOUT_S = 300
SAVE_TIMEOUT_S = 300  # le port indexe l'élément de mémoire `offre` et cherche les doublons

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: GapAnalysisState) -> GapAnalysisState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: GapAnalysisState) -> GapAnalysisState:
        view = await deps.ports.gap.posting(deps.user_id, state["posting_id"])
        reused = view.analysis is not None
        logger.info(
            "Offre lue : session %s, offre %s, analyse déjà rangée %s",
            deps.session_id,
            view.posting_id,
            reused,
        )
        analysis = view.analysis.model_dump(mode="json") if view.analysis else None
        return {"analysis": analysis, "reused": reused}

    return load


def route_load(state: GapAnalysisState) -> str:
    return "match" if state.get("analysis") else "analyze"


async def _ask_analysis(deps: GraphDeps, text: str) -> tuple[PostingAnalysis, list[Problem]]:
    """Une demande, puis deux re-demandes au plus ; rend la meilleure analyse (`better_answer`)
    et ses problèmes."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **analyze_vars(text))
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(ANALYZE_REQUEST)]
    best: tuple[PostingAnalysis, list[Problem]] | None = None
    for ask in range(1, MAX_ANALYZE_ASKS + 1):
        if best is not None:
            messages += [AIMessage(best[0].model_dump_json()), HumanMessage(problems_text(best[1]))]
        found = await structured_call(
            model,
            PostingAnalysis,
            messages,
            agent=AGENT,
            step=f"analyse-{ask}",
            intent="j'analyse l'offre" if ask == 1 else "je corrige l'analyse de l'offre",
        )
        best = better_answer(best, found, analysis_problems(found, text))
        if not best[1]:
            break
    assert best is not None
    return best


def make_analyze(deps: GraphDeps) -> Node:
    @node_timeout(ANALYZE_TIMEOUT_S)
    async def analyze(state: GapAnalysisState) -> GapAnalysisState:
        """L'analyse de l'Analyste, vérifiée ; rejoué, il redemande sans rien écrire."""
        view = await deps.ports.gap.posting(deps.user_id, state["posting_id"])
        if not enough_text(view.text):  # même borne que la route (revue 6.5, m6) : aucun appel
            logger.info(
                "Offre trop courte : session %s, offre %s", deps.session_id, view.posting_id
            )
            return {"analysis": None, "reused": False, "rejection": TOO_SHORT}
        if len(view.text) > MAX_POSTING_CHARS:
            logger.info(
                "Offre tronquée pour l'analyse : session %s, offre %s, %d caractères sur %d",
                deps.session_id,
                view.posting_id,
                MAX_POSTING_CHARS,
                len(view.text),
            )
        found, problems = await _ask_analysis(deps, view.text)
        analysis, dropped = drop_absent_keywords(found, view.text)
        if problems:
            logger.info(
                "Analyse gardée avec %d problème(s) : session %s, offre %s, %d mot(s) clé(s) "
                "retiré(s)",
                len(problems),
                deps.session_id,
                view.posting_id,
                dropped,
            )
        return {"analysis": analysis.model_dump(mode="json"), "reused": False}

    return analyze


def route_analyze(state: GapAnalysisState) -> str:
    analysis = state.get("analysis") or {}
    return "save_analysis" if analysis.get("is_job_posting") else "reject"


def make_reject(deps: GraphDeps) -> Node:
    @node_timeout()
    async def reject(state: GapAnalysisState) -> GapAnalysisState:
        reason = state.get("rejection") or NOT_A_POSTING
        await deps.ports.gap.reject(deps.user_id, state["posting_id"], reason)
        logger.info("Offre refusée : session %s, offre %s", deps.session_id, state["posting_id"])
        _say("refus", reason)
        return {"summary": reason}

    return reject


def make_save_analysis(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save_analysis(state: GapAnalysisState) -> GapAnalysisState:
        """La première analyse rangée gagne : la suite lit celle qui est en base."""
        assert state["analysis"] is not None  # garanti par `route_analyze`
        found = PostingAnalysis.model_validate(state["analysis"])
        saved = await deps.ports.gap.save_analysis(
            deps.user_id, deps.session_id, state["posting_id"], found
        )
        logger.info(
            "Analyse rangée : session %s, offre %s, première %s, %d doublon(s)",
            deps.session_id,
            saved.posting_id,
            saved.first,
            len(saved.duplicates),
        )
        return {
            "analysis": saved.analysis.model_dump(mode="json"),
            "duplicates": duplicates_json(saved),
        }

    return save_analysis


async def _ask_matches(
    deps: GraphDeps, analysis: PostingAnalysis, known: list[KnownSkill]
) -> SkillMatches | None:
    """Le rattachement demandé au modèle ; sans besoin ou sans référentiel, aucun appel."""
    if not analysis.skills or not known:
        return None
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **match_vars(analysis, known))
    return await structured_call(
        model,
        SkillMatches,
        [SystemMessage(prompt), HumanMessage(MATCH_REQUEST)],
        agent=AGENT,
        step="rattachement",
        intent="je rattache les compétences de l'offre aux tiennes",
    )


def make_match(deps: GraphDeps) -> Node:
    @node_timeout(MATCH_TIMEOUT_S)
    async def match(state: GapAnalysisState) -> GapAnalysisState:
        assert state["analysis"] is not None  # garanti par `route_load` et `save_analysis`
        analysis = PostingAnalysis.model_validate(state["analysis"])
        known = await deps.ports.gap.known_skills(deps.user_id)
        found = await _ask_matches(deps, analysis, known)
        matches, unknown = clean_matches(analysis, found, known)
        logger.info(
            "Rattachement : session %s, offre %s, %d besoin(s), %d rattaché(s), %d réponse(s) "
            "hors besoins ou hors référentiel ignorée(s)",
            deps.session_id,
            state["posting_id"],
            len(matches),
            sum(m.known is not None for m in matches),
            unknown,
        )
        return {"matches": [m.model_dump() for m in matches]}

    return match


def make_save_gap(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save_gap(state: GapAnalysisState) -> GapAnalysisState:
        """Lignes et score calculés par le code du port (idempotent par session)."""
        matches = [SkillMatch.model_validate(m) for m in state.get("matches", [])]
        saved = await deps.ports.gap.save_gap(
            deps.user_id, deps.session_id, state["posting_id"], matches
        )
        logger.info(
            "Écart rangé : session %s, offre %s, score %d, %d ligne(s), %d absente(s)",
            deps.session_id,
            state["posting_id"],
            saved.score,
            saved.rows,
            saved.missing,
        )
        return {"saved": saved_json(saved)}

    return save_gap


def announce(state: GapAnalysisState) -> GapAnalysisState:
    """Le score, les compétences absentes, le doublon éventuel, puis l'écart prêt."""
    text = gap_text(GapSaved(**state["saved"]))
    _say("ecart", text)
    if duplicate := duplicate_text(state.get("duplicates", [])):
        _say("doublon", duplicate)
        text = f"{text} {duplicate}"
    posting_id = state["posting_id"]
    analysis = state["analysis"] or {}
    artifact = {
        "artifact_id": posting_id,
        "kind": "posting_gap",
        "title": str(analysis.get("title") or "Offre"),
        "url": f"/carriere/offres/{posting_id}",
    }
    emit("artifact.ready", artifact, agent=AGENT)
    return {"summary": text}

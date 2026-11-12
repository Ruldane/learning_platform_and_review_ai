"""Le Vérificateur contrôle la leçon du Rédacteur (SPEC 3.5, 9.1, D90) : les contrôles
déterministes (`check_lesson` : structure, longueur, liens, recopie), puis un contrôle des faits
par le modèle (`FactReport`) : chaque affirmation sur le domaine doit s'appuyer sur une source
numérotée. La leçon et les sources sont des données encadrées, jamais des consignes.

Seules les sections de faits sont jugées : une affirmation située ailleurs (objectif, exercice,
auto-évaluation…) est écartée (`in_scope`). Après la dernière révision, s'il ne reste que des
affirmations non sourcées, le code retire lui-même les phrases qui les portent (`prune`, sans
appel au modèle) puis rejoue les contrôles déterministes (D97 n° 11).

Rien n'est écrit : un nœud rejoué refait le contrôle, sans effet de bord."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.nodes.lesson_common import (
    LessonSource,
    Node,
    brief_of,
    lesson_sources,
    sources_prompt,
)
from app.agents.nodes.verifier.checks import check_lesson
from app.agents.nodes.verifier.prune import in_scope, prune, still_cited
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.lesson_factory import LessonFactoryState

AGENT = "verifier"
MAX_REVISIONS = 2  # révisions demandées au Rédacteur au plus : trois écritures en tout
VERIFY_TIMEOUT_S = 240
MAX_CLAIM_CHARS = 300
MAX_PROBLEMS_SHOWN = 6

logger = logging.getLogger(__name__)


class FactReport(BaseModel):
    unsupported: list[str] = Field(default_factory=list, max_length=20)


def _numbered(sources: list[LessonSource]) -> list[tuple[int, str, str]]:
    return [(s.number, s.url, s.text) for s in sources]


async def _facts(deps: GraphDeps, title: str, draft: str, sources: list[LessonSource]) -> list[str]:
    prompt = render_prompt(
        AGENT,
        title=title,
        sources=sources_prompt(sources),
        lesson=untrusted(draft, "leçon"),
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    report = await structured_call(
        model,
        FactReport,
        [SystemMessage(prompt), HumanMessage("Contrôle les faits de cette leçon.")],
        agent=AGENT,
        step="faits",
        intent="je contrôle les faits de la leçon",
    )
    claims = (" ".join(c.split())[:MAX_CLAIM_CHARS] for c in report.unsupported)
    return [claim for claim in claims if claim]


def _converge(
    draft: str, title: str, sources: list[LessonSource], unsupported: list[str]
) -> tuple[LessonFactoryState, int]:
    """Dernière révision passée, seuls des faits non sourcés restent : leurs phrases sont retirées
    si toutes sont situées et si la leçon tient encore les contrôles ; sinon, la raison de
    l'échec. Rend la mise à jour de l'état et le nombre de phrases retirées."""
    pruned = prune(draft, unsupported)
    if pruned.unlocated:
        problem = (
            f"Retrait impossible : {pruned.unlocated} affirmation(s) non sourcée(s) introuvable(s) "
            "dans les sections de faits (citation absente, ambiguë ou trop courte)."
        )
        return {"problems": [problem]}, 0
    if left := still_cited(pruned.markdown, unsupported):
        problem = f"Retrait incomplet : {left} affirmation(s) non sourcée(s) encore dans la leçon."
        return {"problems": [problem]}, 0
    check = check_lesson(pruned.markdown, title=title, sources=_numbered(sources))
    if check.problems:
        lead = f"Retrait de {pruned.removed} phrase(s) non sourcée(s) impossible"
        return {"problems": [f"{lead} : {p}" for p in check.problems]}, 0
    update: LessonFactoryState = {"draft": pruned.markdown, "words": check.words, "unsupported": []}
    return update, pruned.removed


def _verdict_text(words: int, problems: list[str], unsupported: list[str], removed: int) -> str:
    if not problems and not unsupported:
        after = f" après retrait de {removed} phrase(s) non sourcée(s)" if removed else ""
        return f"Leçon conforme{after} : {words} mots, structure, liens et faits sourcés vérifiés."
    lines = [f"Leçon à corriger ({words} mots) :"]
    lines += [f"- {p}" for p in problems[:MAX_PROBLEMS_SHOWN]]
    if len(problems) > MAX_PROBLEMS_SHOWN:
        lines.append(f"- … et {len(problems) - MAX_PROBLEMS_SHOWN} autres problèmes.")
    if unsupported:
        lines.append(f"- {len(unsupported)} affirmation(s) non sourcée(s).")
    return "\n".join(lines)


def make_verify(deps: GraphDeps) -> Node:
    @node_timeout(VERIFY_TIMEOUT_S)
    async def verify(state: LessonFactoryState) -> LessonFactoryState:
        brief = brief_of(state)
        draft = state["draft"]
        sources = lesson_sources(state)
        check = check_lesson(draft, title=brief.title, sources=_numbered(sources))
        claims = await _facts(deps, brief.title, draft, sources)
        unsupported = in_scope(draft, claims)
        revisions = state.get("revisions", 0)
        logger.info(
            "Leçon contrôlée : session %s, module %s, %d mots, %d problème(s), "
            "%d non sourcée(s), %d hors périmètre",
            deps.session_id,
            brief.module_id,
            check.words,
            len(check.problems),
            len(unsupported),
            len(claims) - len(unsupported),
        )
        result: LessonFactoryState = {
            "words": check.words,
            "problems": check.problems,
            "unsupported": unsupported,
        }
        removed = 0
        if revisions >= MAX_REVISIONS and unsupported and not check.problems:
            update, removed = _converge(draft, brief.title, sources, unsupported)
            result.update(update)
            logger.info(
                "Leçon élaguée : session %s, module %s, %d phrase(s) retirée(s), %d problème(s)",
                deps.session_id,
                brief.module_id,
                removed,
                len(result.get("problems", [])),
            )
        text = _verdict_text(result["words"], result["problems"], result["unsupported"], removed)
        emit(
            "agent.message",
            {"message_id": f"{AGENT}-controle-{revisions}", "text": text},
            agent=AGENT,
        )
        return result

    return verify


def route_verify(state: LessonFactoryState) -> str:
    """Rien à corriger : publier. Sinon une révision du Rédacteur, deux au plus, puis l'échec."""
    if not state.get("problems") and not state.get("unsupported"):
        return "publish"
    return "write" if state.get("revisions", 0) < MAX_REVISIONS else "fail_lesson"

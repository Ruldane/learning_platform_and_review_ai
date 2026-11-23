"""Le Vérificateur contrôle la leçon du Rédacteur (SPEC 3.5, 9.1, D90) : les contrôles
déterministes (`check_lesson` : structure, longueur, liens, recopie), puis un contrôle des faits
par le modèle (`FactReport`) : chaque affirmation sur le domaine doit s'appuyer sur une source
numérotée. La leçon et les sources sont des données encadrées, jamais des consignes.

Seules les sections de faits sont jugées : une affirmation située ailleurs (objectif, exercice,
auto-évaluation…) est écartée (`in_scope`). Après la dernière révision, s'il ne reste que des
affirmations non sourcées, le code retire les phrases qui les portent (`prune`), puis rejoue
les contrôles et note la version élaguée (D97 n° 11, D225).

Rien n'est écrit : un nœud rejoué refait le contrôle, sans effet de bord."""

import logging
from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.nodes.lesson_common import (
    LessonSource,
    Node,
    brief_of,
    lesson_sources,
    module_prompt,
    sources_prompt,
)
from app.agents.nodes.verifier.checks import check_lesson
from app.agents.nodes.verifier.grades import CRITERIA, MIN_GRADE, LessonGrades
from app.agents.nodes.verifier.prune import in_scope, prune, still_cited
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.played_model import refresh_updated_brief
from app.agents.runtime.structured import structured_call
from app.agents.state.lesson_factory import LessonFactoryState
from app.agents.tools.lesson_port import ModuleBrief

AGENT = "verifier"
MAX_REVISIONS = 2  # révisions demandées au Rédacteur au plus : trois écritures en tout
VERIFY_TIMEOUT_S = 240
MAX_CLAIM_CHARS = 300
MAX_PROBLEMS_SHOWN = 6
REVERTED = "Cette révision est moins bonne que la précédente : je repars de la meilleure version."

logger = logging.getLogger(__name__)


class FactReport(BaseModel):
    unsupported: list[str] = Field(default_factory=list, max_length=20)
    grades: LessonGrades

    def claims(self) -> list[str]:
        claims = (" ".join(c.split())[:MAX_CLAIM_CHARS] for c in self.unsupported)
        return [claim for claim in claims if claim]


def _numbered(sources: list[LessonSource]) -> list[tuple[int, str, str]]:
    return [(s.number, s.url, s.text) for s in sources]


async def _facts(
    deps: GraphDeps,
    brief: ModuleBrief,
    draft: str,
    sources: list[LessonSource],
    *,
    step: str = "faits",
) -> FactReport:
    prompt = render_prompt(
        AGENT,
        title=untrusted(brief.title, "titre de la leçon"),
        module=module_prompt(brief),
        sources=sources_prompt(sources),
        lesson=untrusted(draft, "leçon"),
        min_grade=MIN_GRADE,
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        refresh_updated_brief(model),
        FactReport,
        [SystemMessage(prompt), HumanMessage("Contrôle les faits de cette leçon.")],
        agent=AGENT,
        step=step,
        intent="je contrôle les faits de la leçon",
    )


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
        return {
            "problems": [problem],
            "check_categories": ["Retrait des affirmations non sourcées"],
        }, 0
    if left := still_cited(pruned.markdown, unsupported):
        problem = f"Retrait incomplet : {left} affirmation(s) non sourcée(s) encore dans la leçon."
        return {
            "problems": [problem],
            "check_categories": ["Retrait des affirmations non sourcées"],
        }, 0
    check = check_lesson(pruned.markdown, title=title, sources=_numbered(sources))
    if check.problems:
        lead = f"Retrait de {pruned.removed} phrase(s) non sourcée(s) impossible"
        return {
            "problems": [f"{lead} : {p}" for p in check.problems],
            "check_categories": list(check.categories),
        }, 0
    update: LessonFactoryState = {"draft": pruned.markdown, "words": check.words, "unsupported": []}
    return update, pruned.removed


async def _review_after_pruning(
    deps: GraphDeps,
    brief: ModuleBrief,
    draft: str,
    sources: list[LessonSource],
    unsupported: list[str],
) -> tuple[LessonFactoryState, int]:
    update, removed = _converge(draft, brief.title, sources, unsupported)
    if removed:
        final = update["draft"]
        report = await _facts(deps, brief, final, sources, step="faits-apres-retrait")
        update["scores"] = report.grades.scores()
        update["problems"] = report.grades.problems()
        update["unsupported"] = in_scope(final, report.claims())
    return update, removed


def _verdict_text(result: LessonFactoryState, removed: int, *, show_details: bool = True) -> str:
    words, problems, unsupported = result["words"], result["problems"], result["unsupported"]
    scores = result["scores"]
    grades = [f"- {label} — {scores[name]}/100" for name, label in CRITERIA.items()]
    if not problems and not unsupported:
        after = f" après retrait de {removed} phrase(s) non sourcée(s)" if removed else ""
        return "\n".join([f"Leçon conforme{after} ({words} mots).", *grades])
    lines = [f"Leçon à corriger ({words} mots) :"]
    if show_details:
        lines += [f"- {p}" for p in problems[:MAX_PROBLEMS_SHOWN]]
    else:
        lines += [f"- {category}" for category in result.get("check_categories", [])]
    if show_details and len(problems) > MAX_PROBLEMS_SHOWN:
        lines.append(f"- … et {len(problems) - MAX_PROBLEMS_SHOWN} autres problèmes.")
    if unsupported:
        lines.append(f"- {len(unsupported)} affirmation(s) non sourcée(s).")
    return "\n".join([*lines, *grades])


def draft_rank(*, problems: list[str], unsupported: list[str], scores: dict[str, int]) -> list[int]:
    """Rang d'une version, plus petit = meilleure (D305) : les problèmes de contrôle d'abord
    (les affirmations non sourcées peuvent encore être retirées), puis ces affirmations, puis la
    plus basse des notes."""
    return [len(problems), len(unsupported), -min(scores.values(), default=0)]


def _keep_best(state: LessonFactoryState, result: LessonFactoryState) -> bool:
    """Garde la meilleure version contrôlée dans `best` ; si la nouvelle est moins bonne, l'état
    revient à la meilleure (brouillon, contrôles, notes) et la révision suivante en part. Rend
    `True` dans ce cas."""
    rank = draft_rank(
        problems=result["problems"], unsupported=result["unsupported"], scores=result["scores"]
    )
    best = state.get("best")
    if best is not None and rank > best["rank"]:
        result.update(cast(LessonFactoryState, {k: v for k, v in best.items() if k != "rank"}))
        return True
    result["best"] = {"rank": rank, "draft": state["draft"], **result}
    return False


async def _check(
    deps: GraphDeps, brief: ModuleBrief, draft: str, sources: list[LessonSource]
) -> LessonFactoryState:
    """Contrôles déterministes et contrôle des faits d'une version, journalisés en nombres."""
    check = check_lesson(draft, title=brief.title, sources=_numbered(sources))
    report = await _facts(deps, brief, draft, sources)
    claims = report.claims()
    unsupported = in_scope(draft, claims)
    problems = [*check.problems, *report.grades.problems()]
    logger.info(
        "Leçon contrôlée : session %s, module %s, %d mots, %d problème(s), "
        "%d non sourcée(s), %d hors périmètre",
        deps.session_id,
        brief.module_id,
        check.words,
        len(problems),
        len(unsupported),
        len(claims) - len(unsupported),
    )
    return {
        "words": check.words,
        "problems": problems,
        "unsupported": unsupported,
        "scores": report.grades.scores(),
        "check_categories": list(check.categories),
    }


def make_verify(deps: GraphDeps) -> Node:
    @node_timeout(VERIFY_TIMEOUT_S)
    async def verify(state: LessonFactoryState) -> LessonFactoryState:
        brief = brief_of(state)
        draft = state["draft"]
        sources = lesson_sources(state)
        revisions = state.get("revisions", 0)
        result = await _check(deps, brief, draft, sources)
        removed = 0
        reverted = _keep_best(state, result)
        draft, unsupported = result.get("draft", draft), result["unsupported"]
        if revisions >= MAX_REVISIONS and unsupported and not result["problems"]:
            update, removed = await _review_after_pruning(deps, brief, draft, sources, unsupported)
            result.update(update)
            logger.info(
                "Leçon élaguée : session %s, module %s, %d phrase(s) retirée(s), %d problème(s)",
                deps.session_id,
                brief.module_id,
                removed,
                len(result.get("problems", [])),
            )
        text = _verdict_text(result, removed, show_details=not state.get("verification", False))
        if reverted:
            text = f"{REVERTED}\n{text}"
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

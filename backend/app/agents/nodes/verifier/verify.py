"""Check the Writer's lesson (SPEC 3.5, 9.1, D90).

`check_lesson` validates structure, length, links, and copied passages. The model then
checks whether claims in sections that present facts are backed by numbered sources. The
lesson and source text are supplied as untrusted data.

After the last revision, if unsupported claims are the only remaining issue, `prune`
removes their sentences and verification runs again (D97 item 11, D225). Replaying the
node reruns the checks without writing to storage.
"""

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
MAX_REVISIONS = 2  # At most three drafts including the initial one.
VERIFY_TIMEOUT_S = 240
MAX_CLAIM_CHARS = 300
MAX_PROBLEMS_SHOWN = 6
REVERTED = "I kept the earlier draft because it scored better."
PRUNING_CATEGORY = "Removal of unsupported claims"

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
        title=untrusted(brief.title, "lesson title"),
        module=module_prompt(brief),
        sources=sources_prompt(sources),
        lesson=untrusted(draft, "lesson"),
        min_grade=MIN_GRADE,
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        refresh_updated_brief(model),
        FactReport,
        [SystemMessage(prompt), HumanMessage("Check the facts in this lesson.")],
        agent=AGENT,
        step=step,
        intent="checking the facts in the lesson",
    )


def _converge(
    draft: str, title: str, sources: list[LessonSource], unsupported: list[str]
) -> tuple[LessonFactoryState, int]:
    """Remove unsupported claims when all can be located and the result still passes checks."""
    pruned = prune(draft, unsupported)
    if pruned.unlocated:
        problem = (
            f"Could not locate unsupported claims in factual sections ({pruned.unlocated}). "
            "The quoted text was missing, ambiguous, or too short."
        )
        return {
            "problems": [problem],
            "check_categories": [PRUNING_CATEGORY],
        }, 0
    if left := still_cited(pruned.markdown, unsupported):
        problem = f"Unsupported claims remain in the lesson after removal ({left})."
        return {
            "problems": [problem],
            "check_categories": [PRUNING_CATEGORY],
        }, 0
    check = check_lesson(pruned.markdown, title=title, sources=_numbered(sources))
    if check.problems:
        lead = f"Removing unsupported sentences ({pruned.removed}) made the lesson invalid."
        return {
            "problems": [f"{lead} {p}" for p in check.problems],
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
        after = f" after removing unsupported sentences ({removed})" if removed else ""
        return "\n".join([f"Lesson passed{after} ({words:,} words).", *grades])
    lines = [f"Lesson needs revision ({words:,} words)."]
    if show_details:
        lines += [f"- {p}" for p in problems[:MAX_PROBLEMS_SHOWN]]
    else:
        lines += [f"- {category}" for category in result.get("check_categories", [])]
    if show_details and len(problems) > MAX_PROBLEMS_SHOWN:
        lines.append(f"- Additional problems: {len(problems) - MAX_PROBLEMS_SHOWN}.")
    if unsupported:
        lines.append(f"- Unsupported claims: {len(unsupported)}.")
    return "\n".join([*lines, *grades])


def draft_rank(*, problems: list[str], unsupported: list[str], scores: dict[str, int]) -> list[int]:
    """Rank drafts by fewest problems, fewest unsupported claims, then highest minimum grade."""
    return [len(problems), len(unsupported), -min(scores.values(), default=0)]


def _keep_best(state: LessonFactoryState, result: LessonFactoryState) -> bool:
    """Keep the best draft, checks, and grades for the next revision. Return whether it reverted."""
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
    deps: GraphDeps,
    brief: ModuleBrief,
    draft: str,
    sources: list[LessonSource],
    *,
    allow_legacy: bool,
) -> LessonFactoryState:
    """Run deterministic checks and fact-checking, logging counts and identifiers."""
    check = check_lesson(
        draft, title=brief.title, sources=_numbered(sources), allow_legacy=allow_legacy
    )
    report = await _facts(deps, brief, draft, sources)
    claims = report.claims()
    unsupported = in_scope(draft, claims)
    problems = [*check.problems, *report.grades.problems()]
    logger.info(
        "Lesson checked: session %s, module %s, %d words, %d problems, "
        "%d unsupported claims, %d out of scope",
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
        result = await _check(
            deps, brief, draft, sources, allow_legacy=state.get("verification", False)
        )
        removed = 0
        reverted = _keep_best(state, result)
        draft, unsupported = result.get("draft", draft), result["unsupported"]
        if revisions >= MAX_REVISIONS and unsupported and not result["problems"]:
            update, removed = await _review_after_pruning(deps, brief, draft, sources, unsupported)
            result.update(update)
            logger.info(
                "Lesson pruned: session %s, module %s, %d sentences removed, %d problems",
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
    """Publish a passing draft or ask the Writer to revise within the revision limit."""
    if not state.get("problems") and not state.get("unsupported"):
        return "publish"
    return "write" if state.get("revisions", 0) < MAX_REVISIONS else "fail_lesson"

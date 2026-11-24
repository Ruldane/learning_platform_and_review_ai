"""Load the module brief, report the outcome, and advance the lesson pipeline (D90).

These nodes use `LessonStore`. Writes are idempotent per module so that a node can
resume after a stop without inserting duplicate rows (SPEC 9.4).
"""

import logging
from dataclasses import asdict, replace

from app.agents.nodes.lesson_common import Node, brief_of, kept_verdicts
from app.agents.nodes.verifier.grades import CRITERIA, MIN_GRADE
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.lesson_factory import LessonFactoryState
from app.agents.tools.lesson_port import MAX_SEED_URLS, LessonReport, ResourcePick

MAX_QUERY_CHARS = 300
MAX_REASON_CHARS = 300
MAX_FEEDBACK = 30  # Include check problems, five grades, and up to twenty claims.
MAX_FEEDBACK_CHARS = 600
PUBLISH_TIMEOUT_S = 300  # Allow time to store the lesson, copy PDFs, and render its PDF.
NO_SOURCE = "No sources for this module met the minimum score of 60."
logger = logging.getLogger(__name__)


def module_query(title: str, skills: tuple[str, ...], theme: str) -> str:
    """Build a query from the title, skills, and weekly theme, clipped at a word boundary."""
    text = " ".join(", ".join([title, *skills, theme]).split())
    if len(text) <= MAX_QUERY_CHARS:
        return text
    return text[:MAX_QUERY_CHARS].rsplit(" ", 1)[0].rstrip(",") or text[:MAX_QUERY_CHARS]


def make_brief(deps: GraphDeps) -> Node:
    @node_timeout()
    async def brief(state: LessonFactoryState) -> LessonFactoryState:
        """Load the module brief and use the Council's pages as initial source URLs."""
        found = await deps.ports.lessons.brief(deps.user_id, state["module_id"])
        query = module_query(found.title, found.skills, found.week_theme)
        extra: LessonFactoryState = {}
        urls = list(found.seed_urls)
        if state.get("verification"):
            submitted = await deps.ports.lessons.submission(
                deps.user_id, deps.session_id, state["module_id"]
            )
            found = replace(found, title=submitted.title)
            extra = {"draft": submitted.markdown, "citation_urls": list(submitted.urls)}
            urls = list(dict.fromkeys([*submitted.urls, *urls]))
        return {
            **extra,
            "brief": asdict(found),
            "query": query,
            "urls": urls[:MAX_SEED_URLS],
        }

    return brief


def route_resources(state: LessonFactoryState) -> str:
    """Fail early if no accepted sources can support the lesson."""
    if not kept_verdicts(state):
        return "fail_lesson"
    return "verify" if state.get("verification") else "write"


def route_next(state: LessonFactoryState) -> str:
    """Direct submissions verify one module and leave the rest of the program queued."""
    return "__end__" if state.get("verification") else "next"


def make_publish(deps: GraphDeps) -> Node:
    @node_timeout(PUBLISH_TIMEOUT_S)
    async def publish(state: LessonFactoryState) -> LessonFactoryState:
        """Store the lesson and resources idempotently, then announce publication."""
        brief = brief_of(state)
        report = LessonReport(
            words=state["words"],
            unsupported=(),
            problems=tuple(state.get("resource_notes", [])),
            revisions=state.get("revisions", 0),
            scores=state.get("scores", {}),
        )
        picks = [ResourcePick.model_validate(r) for r in state.get("resources", [])]
        done = await deps.ports.lessons.publish(
            deps.user_id,
            deps.session_id,
            brief.module_id,
            markdown=state["draft"],
            resources=picks,
            report=report,
            verification=state.get("verification", False),
        )
        logger.info(
            "Lesson published: session %s, module %s, lesson %s, %d resources",
            deps.session_id,
            brief.module_id,
            done.lesson_id,
            done.resources,
        )
        pdf = "The PDF is ready." if done.pdf_ok else "The PDF is temporarily unavailable."
        text = f"Lesson published ({state['words']:,} words, {done.resources} resources). {pdf}"
        emit("agent.message", {"message_id": "writer-publication", "text": text}, agent="writer")
        emit(
            "artifact.ready",
            {
                "artifact_id": done.lesson_id,
                "kind": "lesson",
                "title": brief.title,
                "url": f"/learn/lessons/{done.lesson_id}",
            },
            agent="writer",
        )
        return {"published": asdict(done), "summary": f"Published the lesson “{brief.title}”."}

    return publish


def _reason(state: LessonFactoryState) -> str:
    if not kept_verdicts(state):
        return NO_SOURCE
    remaining = [*state.get("problems", []), *state.get("unsupported", [])]
    text = f"Checks still failing after revisions ({state.get('revisions', 0)}). "
    if state.get("verification"):
        return (text + ", ".join(_remaining_checks(state)))[:MAX_REASON_CHARS]
    return (text + "; ".join(remaining))[:MAX_REASON_CHARS]


def _remaining_checks(state: LessonFactoryState) -> list[str]:
    scores = state.get("scores", {})
    items = [
        f"{label} ({scores[key]}/100)"
        for key, label in CRITERIA.items()
        if key in scores and scores[key] < MIN_GRADE
    ]
    items.extend(state.get("check_categories", []))
    if state.get("unsupported"):
        items.append("unsupported claims")
    return items or ["chapter checks"]


def feedback_of(state: LessonFactoryState) -> list[str]:
    """Return a bounded list of problems, grade feedback, and unsupported claims (D308)."""
    remarks = [*state.get("problems", []), *state.get("unsupported", [])]
    return [remark[:MAX_FEEDBACK_CHARS] for remark in remarks[:MAX_FEEDBACK]]


def make_fail_lesson(deps: GraphDeps) -> Node:
    @node_timeout()
    async def fail_lesson(state: LessonFactoryState) -> LessonFactoryState:
        """Record the failure and its reason idempotently before advancing."""
        brief = brief_of(state)
        reason = _reason(state)
        verification = state.get("verification", False)
        await deps.ports.lessons.fail(
            deps.user_id,
            deps.session_id,
            brief.module_id,
            reason,
            verification=verification,
            feedback=feedback_of(state) if verification else (),
        )
        logger.info("Lesson failed: session %s, module %s", deps.session_id, brief.module_id)
        emit(
            "agent.message",
            {"message_id": "writer-echec", "text": f"The lesson could not be published. {reason}"},
            agent="writer",
        )
        summary = (
            "The draft could not be published."
            if state.get("verification")
            else f'The lesson "{brief.title}" could not be published.'
        )
        return {"failure": reason, "summary": summary}

    return fail_lesson


def make_next(deps: GraphDeps) -> Node:
    @node_timeout()
    async def next_lesson(state: LessonFactoryState) -> LessonFactoryState:
        """Continue the program after either outcome and return the next module ID, if any."""
        following = await deps.ports.lessons.next_module(
            deps.user_id, state["program_id"], exclude_session_id=deps.session_id
        )
        logger.info(
            "Next module: session %s, program %s, %s",
            deps.session_id,
            state["program_id"],
            following or "none",
        )
        return {"next_module": following}

    return next_lesson

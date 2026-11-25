"""The review output (SPEC 5.3, D129): "What would you like to do next?", in a loop.

`ask_output` only does `interrupt()` then parses the answer (pure): no write or paid call
before the stop, the node is replayed from its beginning on resume (SPEC 9.4). Accepted
answers: `"report"`, `"finish"`, `{"choice": "report" | "finish"}` and `{"choice": "pdf",
"version_id": ...}` (the version is created by the route `POST /cv/reviews/{id}/generate`,
6.14); an unknown shape, or "pdf" without a version, asks the question again without writing
anything.

`apply_output`: report -> `artifact.ready` (`cv_report`); PDF -> `render_version` (idempotent:
an already rendered version is reread) then `artifact.ready` (`cv_pdf`), or the "exceeds"
sentence; then the question comes back. `close` ("Finish") closes the review (idempotent).

Logs: identifiers and numbers, never the file name (17.2)."""

import logging
from typing import Any, Literal, Protocol

from langgraph.types import interrupt
from pydantic import BaseModel, Field, ValidationError

from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.cv_review import CvReviewState
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, LAYOUT_TIMEOUT_S

AGENT = "recruiter"
OUTPUT_KIND = "cv_output"
QUESTION = "What would you like to do next?"
OPTIONS = [
    {"value": "report", "label": "View the report"},
    {"value": "pdf", "label": "Generate PDF"},
    {"value": "finish", "label": "Finish"},
]
REPORT_URL = "/career/cv/reviews/{review_id}#report"
PDF_URL = "/api/v1/cv/versions/{version_id}/pdf"
RENDER_FAILED = "The PDF could not be generated. Try again in a moment."
CLOSED = "Review complete. Your changes and versions are saved in the review."
# Rendering, extraction and up to three tightenings (6.14), each re-rendered.
RENDER_TIMEOUT_S = 4 * (HTML_RENDER_TIMEOUT_S + LAYOUT_TIMEOUT_S) + 30

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvReviewState) -> CvReviewState: ...


class OutputAnswer(BaseModel):
    choice: Literal["report", "pdf", "finish"]
    version_id: str | None = Field(default=None, min_length=1, max_length=36)


def question() -> dict[str, Any]:
    return {"kind": OUTPUT_KIND, "question": QUESTION, "options": OPTIONS, "fields": []}


def parse_output(value: Any) -> OutputAnswer | None:
    """See the module header; `None`: the question is asked again."""
    if value in ("report", "finish"):
        return OutputAnswer(choice=value)
    if not isinstance(value, dict):
        return None
    try:
        answer = OutputAnswer.model_validate(value)
    except ValidationError:
        return None
    if answer.choice == "pdf" and answer.version_id is None:
        return None
    return answer if answer.choice == "pdf" else OutputAnswer(choice=answer.choice)


def ask_output(state: CvReviewState) -> CvReviewState:
    """`interrupt()` alone: nothing before it; the answer is parsed without any port."""
    answer = parse_output(interrupt(question()))
    return {"output": answer.model_dump() if answer is not None else None}


def route_output(state: CvReviewState) -> str:
    return "apply_output" if state.get("output") is not None else "ask_output"


def pages_text(original: int) -> str:
    pages = "1 page" if original == 1 else f"{original} pages"
    return f"The tailored CV exceeds {pages}. Remove a line or allow one more page."


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


async def _pdf(deps: GraphDeps, version_id: str) -> None:
    outcome = await deps.ports.cv_review.render_version(deps.user_id, version_id)
    logger.info(
        "Version rendered: session %s, version %s, status %s, %s page(s)",
        deps.session_id,
        outcome.version_id,
        outcome.status,
        outcome.page_count,
    )
    if outcome.status == "ready":
        artifact = {
            "artifact_id": outcome.version_id,
            "kind": "cv_pdf",
            "title": "Tailored CV (PDF)",
            "url": PDF_URL.format(version_id=outcome.version_id),
        }
        emit("artifact.ready", artifact, agent=AGENT)
    elif outcome.status == "pages_exceeded":
        _say(f"pages-{outcome.version_id}", pages_text(outcome.original_page_count))
    else:
        _say(f"echec-{outcome.version_id}", RENDER_FAILED)


def make_apply_output(deps: GraphDeps) -> Node:
    @node_timeout(RENDER_TIMEOUT_S)
    async def apply_output(state: CvReviewState) -> CvReviewState:
        answer = OutputAnswer.model_validate(state["output"])
        review_id = state["review_id"]
        if answer.choice == "report":
            artifact = {
                "artifact_id": f"rapport-{review_id}",
                "kind": "cv_report",
                "title": "CV review report",
                "url": REPORT_URL.format(review_id=review_id),
            }
            emit("artifact.ready", artifact, agent=AGENT)
        elif answer.choice == "pdf":
            assert answer.version_id is not None  # guaranteed by `parse_output`
            await _pdf(deps, answer.version_id)
        return {}

    return apply_output


def route_apply(state: CvReviewState) -> str:
    output = state.get("output") or {}
    return "close" if output.get("choice") == "finish" else "ask_output"


def make_close(deps: GraphDeps) -> Node:
    @node_timeout()
    async def close(state: CvReviewState) -> CvReviewState:
        await deps.ports.cv_review.close(deps.user_id, state["review_id"])
        logger.info("Review finished: session %s, review %s", deps.session_id, state["review_id"])
        _say("fin", CLOSED)
        return {"summary": CLOSED}

    return close

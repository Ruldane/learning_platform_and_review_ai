"""La sortie de la revue (SPEC 5.3, D129) : « Que veux-tu maintenant ? », en boucle.

`ask_output` ne fait qu'`interrupt()` puis analyse la réponse (pur) : aucune écriture ni appel
payant avant l'arrêt, le nœud est rejoué depuis son début à la reprise (SPEC 9.4). Réponses
admises : `"report"`, `"finish"`, `{"choice": "report" | "finish"}` et `{"choice": "pdf",
"version_id": …}` (la version est créée par la route `POST /cv/reviews/{id}/generate`, 6.14) ; une
forme inconnue, ou « pdf » sans version, repose la question sans rien écrire.

`apply_output` : rapport → `artifact.ready` (`cv_report`) ; PDF → `render_version` (idempotent :
une version déjà rendue est relue) puis `artifact.ready` (`cv_pdf`), ou la phrase « dépasse » ;
puis la question revient. `close` (« Terminer ») ferme la revue (idempotent).

Journaux : identifiants et nombres, jamais le nom du fichier (17.2)."""

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
QUESTION = "Que veux-tu maintenant ?"
OPTIONS = [
    {"value": "report", "label": "Voir le rapport"},
    {"value": "pdf", "label": "Générer le PDF"},
    {"value": "finish", "label": "Terminer"},
]
REPORT_URL = "/career/cv/reviews/{review_id}#rapport"
PDF_URL = "/api/v1/cv/versions/{version_id}/pdf"
RENDER_FAILED = "Le PDF n'a pas pu être généré : réessaie dans un instant."
CLOSED = "Revue terminée. Tes modifications et tes versions restent dans la revue."
# Rendu, extraction et jusqu'à trois resserrements (6.14), chacun re-rendu.
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
    """Voir l'en-tête du module ; `None` : la question est reposée."""
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
    """`interrupt()` seul : rien avant lui ; la réponse est analysée sans aucun port."""
    answer = parse_output(interrupt(question()))
    return {"output": answer.model_dump() if answer is not None else None}


def route_output(state: CvReviewState) -> str:
    return "apply_output" if state.get("output") is not None else "ask_output"


def pages_text(original: int) -> str:
    pages = "1 page" if original == 1 else f"{original} pages"
    return f"Le CV ciblé dépasse {pages} : retire une ligne ou autorise une page de plus."


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


async def _pdf(deps: GraphDeps, version_id: str) -> None:
    outcome = await deps.ports.cv_review.render_version(deps.user_id, version_id)
    logger.info(
        "Version rendue : session %s, version %s, statut %s, %s page(s)",
        deps.session_id,
        outcome.version_id,
        outcome.status,
        outcome.page_count,
    )
    if outcome.status == "ready":
        artifact = {
            "artifact_id": outcome.version_id,
            "kind": "cv_pdf",
            "title": "CV ciblé (PDF)",
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
                "title": "Rapport de la revue du CV",
                "url": REPORT_URL.format(review_id=review_id),
            }
            emit("artifact.ready", artifact, agent=AGENT)
        elif answer.choice == "pdf":
            assert answer.version_id is not None  # garanti par `parse_output`
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
        logger.info("Revue terminée : session %s, revue %s", deps.session_id, state["review_id"])
        _say("fin", CLOSED)
        return {"summary": CLOSED}

    return close

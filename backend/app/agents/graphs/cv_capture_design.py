"""`design` mode of the `cv_capture` graph (SPEC 5.2, D125): the Designer captures the design of
a CV in at most three automatic passes, then January validates or adjusts.

START -> prepare -> sample -> draft -> render
render: score >= TARGET_SCORE, pass = MAX_FIX_PASSES or adjustment -> ask_validate; otherwise fix
fix -> render (description corrected); fix -> ask_validate (no usable description)
ask_validate: `interrupt()` alone (no write, no paid call); invalid answer ->
  ask_validate (same question)
apply_answer: Validate -> finish(ready) -> END; Start over -> finish(failed) -> END;
  Adjust + instruction -> fix (at most 5 adjustments)

Every port write is idempotent (`prepare` per template, `render_pass` per pass,
`finish` per template): a replayed node never renders a pass twice, and `durability="sync"`
(D46) never replays a finished node. The question is asked **whatever the score**: never a
silent failure. The template keeps the **best** of the automatic passes
(`keeps_pass`: on a tie the most recent; an adjustment always replaces);
the question and the final message state the score of the kept pass."""

import logging
from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agents.nodes.designer import AGENT, Node, make_draft, make_fix, make_sample
from app.agents.nodes.designer_steps import DesignAnswer, parse_answer, question
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.cv_capture import CvCaptureState
from app.agents.tools.cv_schema import CvContent
from app.agents.tools.cv_template_port import keeps_pass
from app.agents.tools.template_schema import TemplateSpec
from app.agents.tools.template_similarity import MAX_FIX_PASSES, TARGET_SCORE
from app.providers.fonts.base import FONT_TIMEOUT_S
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, LAYOUT_TIMEOUT_S

__all__ = ["DESIGN_ENTRY", "add_design"]

DESIGN_ENTRY = "prepare"
# Layout (60 s) and two fonts in two weights (15 s each); render (45 s), render extraction
# (60 s) and score (preflight G27: beyond the 120 s default of SPEC 9.6).
PREPARE_TIMEOUT_S = LAYOUT_TIMEOUT_S + 4 * FONT_TIMEOUT_S + 30
RENDER_TIMEOUT_S = HTML_RENDER_TIMEOUT_S + LAYOUT_TIMEOUT_S + 30
ARTIFACT_URL = "/career/cv/templates/{template_id}"
RESTARTED = "Template capture cancelled."

logger = logging.getLogger(__name__)


def make_prepare(deps: GraphDeps) -> Node:
    @node_timeout(PREPARE_TIMEOUT_S)
    async def prepare(state: CvCaptureState) -> CvCaptureState:
        emit(
            "agent.started",
            {"step": "lecture", "intent": "Reading your CV layout"},
            agent=AGENT,
        )
        view = await deps.ports.cv_templates.prepare(deps.user_id, str(state["template_id"]))
        logger.info(
            "Original CV prepared: session %s, template %s, %d page(s), selectable %s",
            deps.session_id,
            view.template_id,
            view.page_count,
            view.selectable,
        )
        return {"selectable": view.selectable, "page_count": view.page_count}

    return prepare


def make_render(deps: GraphDeps) -> Node:
    @node_timeout(RENDER_TIMEOUT_S)
    async def render(state: CvCaptureState) -> CvCaptureState:
        """Next pass, rendered then stored by the port (already rendered: read back)."""
        template_id, pass_no = str(state["template_id"]), state.get("pass_no", 0) + 1
        emit(
            "agent.started",
            {"step": f"rendu-{pass_no}", "intent": "Laying out your CV"},
            agent=AGENT,
        )
        spec = TemplateSpec.model_validate(state["spec"])
        content = CvContent.model_validate(state["sample"])
        adjusted = state.get("adjustments", 0) > 0
        done = await deps.ports.cv_templates.render_pass(
            deps.user_id, template_id, pass_no, spec, content, adjusted
        )
        logger.info(
            "Passe rendue : session %s, gabarit %s, passe %d, score %d",
            deps.session_id,
            template_id,
            pass_no,
            done.score,
        )
        text = f"Pass {pass_no}: the render looks {done.score}% like your CV."
        kept = state.get("kept_score")
        out: CvCaptureState = {"pass_no": pass_no, "score": done.score}
        if keeps_pass(adjusted, done.score, kept):
            out["kept_pass"], out["kept_score"] = pass_no, done.score
            out["kept_spec"] = state["spec"]
        else:  # a worse pass does not replace the best one (the port does the same)
            text += f" I'm keeping pass {state['kept_pass']} ({kept}%)."
        emit("agent.message", {"message_id": f"{AGENT}-passe-{pass_no}", "text": text}, agent=AGENT)
        return out

    return render


def route_render(state: CvCaptureState) -> str:
    """After an adjustment, the question comes straight back; otherwise at most three passes."""
    if state.get("adjustments", 0) > 0:
        return "ask_validate"
    if state["score"] >= TARGET_SCORE or state["pass_no"] >= MAX_FIX_PASSES:
        return "ask_validate"
    return "fix"


def route_fix(state: CvCaptureState) -> str:
    return "ask_validate" if state.get("stalled") else "render"


def kept_score_of(state: CvCaptureState) -> int:
    """The score of the kept pass; a checkpoint from before this field shows the last pass."""
    return state.get("kept_score", state.get("score", 0))


def ask_validate(state: CvCaptureState) -> CvCaptureState:
    """`interrupt()` alone: nothing before it; the answer is parsed without any port."""
    adjustments = state.get("adjustments", 0)
    answer = parse_answer(interrupt(question(kept_score_of(state), adjustments)), adjustments)
    return {"answer": answer.model_dump() if answer is not None else None}


def route_answer(state: CvCaptureState) -> str:
    return "apply_answer" if state.get("answer") is not None else "ask_validate"


def _artifact(template_id: str) -> dict[str, Any]:
    return {
        "artifact_id": f"modele-{template_id}",
        "kind": "cv_template",
        "title": "CV template",
        "url": ARTIFACT_URL.format(template_id=template_id),
    }


def make_apply_answer(deps: GraphDeps) -> Node:
    @node_timeout()
    async def apply_answer(state: CvCaptureState) -> CvCaptureState:
        """Validate or start over: `finish` (idempotent); adjust: the instruction goes to `fix`."""
        answer = DesignAnswer.model_validate(state["answer"])
        template_id = str(state["template_id"])
        if answer.action == "adjust":
            return {
                "adjustments": state.get("adjustments", 0) + 1,
                "instruction": answer.instruction,
            }
        store = deps.ports.cv_templates
        if answer.action == "validate":
            await store.finish(deps.user_id, template_id, "ready", None)
            text = f"CV template ready with a {kept_score_of(state)}% match to your original CV."
        else:
            await store.finish(deps.user_id, template_id, "failed", RESTARTED)
            text = f"{RESTARTED} You can start the template capture again."
        logger.info(
            "Template finished: session %s, template %s, %s, %d pass(es), %d adjustment(s)",
            deps.session_id,
            template_id,
            answer.action,
            state["pass_no"],
            state.get("adjustments", 0),
        )
        emit("agent.message", {"message_id": f"{AGENT}-fin", "text": text}, agent=AGENT)
        if answer.action == "validate":
            emit("artifact.ready", _artifact(template_id), agent=AGENT)
        return {"summary": text}

    return apply_answer


def route_apply(state: CvCaptureState) -> str:
    answer = state["answer"] or {}
    return "fix" if answer.get("action") == "adjust" else END


def add_design(graph: StateGraph[Any, Any, Any, Any], deps: GraphDeps) -> None:
    """The `design` mode nodes; the entry is `DESIGN_ENTRY`, routed by `cv_capture`."""
    graph.add_node("prepare", make_prepare(deps))
    graph.add_node("sample", make_sample(deps))
    graph.add_node("draft", make_draft(deps))
    graph.add_node("render", make_render(deps))
    graph.add_node("fix", make_fix(deps))
    graph.add_node("ask_validate", ask_validate)
    graph.add_node("apply_answer", make_apply_answer(deps))
    graph.add_edge("prepare", "sample")
    graph.add_edge("sample", "draft")
    graph.add_edge("draft", "render")
    graph.add_conditional_edges("render", route_render, ["fix", "ask_validate"])
    graph.add_conditional_edges("fix", route_fix, ["render", "ask_validate"])
    graph.add_conditional_edges("ask_validate", route_answer, ["apply_answer", "ask_validate"])
    graph.add_conditional_edges("apply_answer", route_apply, ["fix", END])

"""Mode `design` du parcours `cv_capture` (SPEC 5.2, D125) : le Maquettiste capture le design
d'un CV en trois passes automatiques au plus, puis January valide ou ajuste.

START -> prepare -> sample -> draft -> render
render : score >= TARGET_SCORE, passe = MAX_FIX_PASSES ou ajustement -> ask_validate ; sinon fix
fix -> render (description corrigée) ; fix -> ask_validate (aucune description valable)
ask_validate : `interrupt()` seul (aucune écriture, aucun appel payant) ; réponse invalide ->
  ask_validate (même question)
apply_answer : Valider -> finish(ready) -> END ; Recommencer -> finish(failed) -> END ;
  Ajuster + consigne -> fix (5 ajustements au plus)

Chaque écriture du port est idempotente (`prepare` par gabarit, `render_pass` par passe,
`finish` par gabarit) : un nœud rejoué ne rend jamais une passe deux fois, et `durability="sync"`
(D46) ne rejoue jamais un nœud terminé. La question est posée **quel que soit le score** : jamais
d'échec silencieux."""

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
from app.agents.tools.template_schema import TemplateSpec
from app.agents.tools.template_similarity import MAX_FIX_PASSES, TARGET_SCORE
from app.providers.fonts.base import FONT_TIMEOUT_S
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, LAYOUT_TIMEOUT_S

__all__ = ["DESIGN_ENTRY", "add_design"]

DESIGN_ENTRY = "prepare"
# Mise en page (60 s) et deux polices en deux graisses (15 s chacune) ; rendu (45 s), extraction
# du rendu (60 s) et score (preflight G27 : au-delà des 120 s par défaut de SPEC 9.6).
PREPARE_TIMEOUT_S = LAYOUT_TIMEOUT_S + 4 * FONT_TIMEOUT_S + 30
RENDER_TIMEOUT_S = HTML_RENDER_TIMEOUT_S + LAYOUT_TIMEOUT_S + 30
ARTIFACT_URL = "/carriere/cv/modeles/{template_id}"
RESTARTED = "Capture abandonnée."

logger = logging.getLogger(__name__)


def make_prepare(deps: GraphDeps) -> Node:
    @node_timeout(PREPARE_TIMEOUT_S)
    async def prepare(state: CvCaptureState) -> CvCaptureState:
        emit(
            "agent.started",
            {"step": "lecture", "intent": "je lis la mise en page de ton CV"},
            agent=AGENT,
        )
        view = await deps.ports.cv_templates.prepare(deps.user_id, str(state["template_id"]))
        logger.info(
            "CV d'origine préparé : session %s, gabarit %s, %d page(s), sélectionnable %s",
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
        """Passe suivante, rendue puis rangée par le port (déjà rendue : relue)."""
        template_id, pass_no = str(state["template_id"]), state.get("pass_no", 0) + 1
        emit(
            "agent.started",
            {"step": f"rendu-{pass_no}", "intent": "je mets ton CV en page"},
            agent=AGENT,
        )
        spec = TemplateSpec.model_validate(state["spec"])
        content = CvContent.model_validate(state["sample"])
        done = await deps.ports.cv_templates.render_pass(
            deps.user_id, template_id, pass_no, spec, content
        )
        logger.info(
            "Passe rendue : session %s, gabarit %s, passe %d, score %d",
            deps.session_id,
            template_id,
            pass_no,
            done.score,
        )
        text = f"Passe {pass_no} : le rendu ressemble à ton CV à {done.score} %."
        emit("agent.message", {"message_id": f"{AGENT}-passe-{pass_no}", "text": text}, agent=AGENT)
        return {"pass_no": pass_no, "score": done.score}

    return render


def route_render(state: CvCaptureState) -> str:
    """Après un ajustement, la question revient aussitôt ; sinon trois passes au plus."""
    if state.get("adjustments", 0) > 0:
        return "ask_validate"
    if state["score"] >= TARGET_SCORE or state["pass_no"] >= MAX_FIX_PASSES:
        return "ask_validate"
    return "fix"


def route_fix(state: CvCaptureState) -> str:
    return "ask_validate" if state.get("stalled") else "render"


def ask_validate(state: CvCaptureState) -> CvCaptureState:
    """`interrupt()` seul : rien avant lui ; la réponse est analysée sans aucun port."""
    adjustments = state.get("adjustments", 0)
    answer = parse_answer(interrupt(question(state["score"], adjustments)), adjustments)
    return {"answer": answer.model_dump() if answer is not None else None}


def route_answer(state: CvCaptureState) -> str:
    return "apply_answer" if state.get("answer") is not None else "ask_validate"


def _artifact(template_id: str) -> dict[str, Any]:
    return {
        "artifact_id": f"modele-{template_id}",
        "kind": "cv_template",
        "title": "Modèle de CV",
        "url": ARTIFACT_URL.format(template_id=template_id),
    }


def make_apply_answer(deps: GraphDeps) -> Node:
    @node_timeout()
    async def apply_answer(state: CvCaptureState) -> CvCaptureState:
        """Valider ou recommencer : `finish` (idempotent) ; ajuster : la consigne part à `fix`."""
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
            text = f"Modèle de CV prêt : il ressemble à ton CV à {state['score']} %."
        else:
            await store.finish(deps.user_id, template_id, "failed", RESTARTED)
            text = f"{RESTARTED} Tu peux relancer la capture du modèle."
        logger.info(
            "Gabarit terminé : session %s, gabarit %s, %s, %d passe(s), %d ajustement(s)",
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
    """Les nœuds du mode `design` ; l'entrée est `DESIGN_ENTRY`, aiguillée par `cv_capture`."""
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

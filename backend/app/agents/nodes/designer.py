"""Le Maquettiste (vision, D125) : parcours `cv_capture`, mode `design`. Il voit les pages du CV.

`sample` : le contenu de démonstration. CV au texte sélectionnable : le modèle le recopie
(`CvContent`, images et blocs), chaque texte absent du CV est redemandé une fois puis retiré ; CV
scanné : le contenu du profil validé (`sample_fallback`), sinon un échec lisible.
`draft` : la description du design (`TemplateSpec`) ; ses défauts (`template_problems`) sont
redemandés deux fois au plus, puis la capture échoue lisiblement.
`fix` : une description corrigée, depuis la description courante, les écarts du score
(`describe`, seulement sous `TARGET_SCORE`), les images d'origine et du rendu, et la consigne de
January si elle existe ; sans description valable, la description courante est gardée
(`stalled`) et la question est posée.

Journaux : identifiants et nombres, jamais un texte, une image ni une police du CV (17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.designer_steps import copy_retry, invented_lines, spec_retry, verbatim
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.cv_capture import CvCaptureState
from app.agents.tools.cv_schema import CvContent
from app.agents.tools.cv_template_port import OriginalView
from app.agents.tools.template_schema import TemplateSpec, template_problems
from app.agents.tools.template_similarity import TARGET_SCORE, describe
from app.agents.tools.vision import MAX_IMAGES, image_message
from app.core.errors import AppError

AGENT = "designer"
SAMPLE_REQUEST = "Recopie le contenu de ce CV, tel quel."
DRAFT_REQUEST = "Décris le design de ce CV."
FIX_REQUEST = "Corrige la description pour rapprocher le rendu de l'original."
MAX_SAMPLE_ASKS = 2  # une demande, puis une re-demande avec les textes absents du CV
MAX_SPEC_ASKS = 3  # une demande, puis deux re-demandes avec les défauts
VISION_TIMEOUT_S = 600  # sorties structurées avec images, et leurs re-demandes
NO_SAMPLE = (
    "Ton CV est une image (scanné) et ton profil maître n'est pas encore validé : valide-le, "
    "puis relance la capture du modèle."
)
NO_SPEC = "Le Maquettiste n'a pas su décrire le design de ce CV. Recommence la capture."

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvCaptureState) -> CvCaptureState: ...


async def _failed(
    deps: GraphDeps, template_id: str, code: str, reason: str, status: int
) -> AppError:
    """Le gabarit passe en `failed` (idempotent) avant que la session échoue : jamais en
    « capture » pour toujours."""
    await deps.ports.cv_templates.finish(deps.user_id, template_id, "failed", reason)
    return AppError(code, reason, status)


async def _view(deps: GraphDeps, state: CvCaptureState) -> OriginalView:
    """Relu par le port (idempotent) : les images ne passent jamais par l'état."""
    return await deps.ports.cv_templates.prepare(deps.user_id, str(state["template_id"]))


async def _copy(deps: GraphDeps, view: OriginalView) -> tuple[CvContent, int]:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, mode="sample", blocks=untrusted(view.blocks_summary, "cv"))
    messages: list[BaseMessage] = [
        SystemMessage(prompt),
        image_message(SAMPLE_REQUEST, view.pages_png),
    ]
    for ask in range(1, MAX_SAMPLE_ASKS + 1):
        found = await structured_call(
            model,
            CvContent,
            messages,
            agent=AGENT,
            step=f"contenu-{ask}",
            intent="je recopie le contenu de ton CV" if ask == 1 else "je recopie mieux",
        )
        invented = invented_lines(found, view.original_text)
        if not invented or ask == MAX_SAMPLE_ASKS:
            return verbatim(found, invented), len(invented)
        messages += [AIMessage(found.model_dump_json()), HumanMessage(copy_retry(invented))]
    raise AssertionError("inatteignable")  # pragma: no cover


def make_sample(deps: GraphDeps) -> Node:
    @node_timeout(VISION_TIMEOUT_S)
    async def sample(state: CvCaptureState) -> CvCaptureState:
        template_id = str(state["template_id"])
        removed = 0
        if state.get("selectable", True):
            content, removed = await _copy(deps, await _view(deps, state))
        else:
            fallback = await deps.ports.cv_templates.sample_fallback(deps.user_id)
            if fallback is None:
                raise await _failed(deps, template_id, "design_no_sample", NO_SAMPLE, 422)
            content = fallback
        logger.info(
            "Contenu de démonstration : session %s, gabarit %s, %d section(s), "
            "%d texte(s) retiré(s)",
            deps.session_id,
            template_id,
            len(content.sections),
            removed,
        )
        return {"sample": content.model_dump(mode="json")}

    return sample


async def ask_spec(
    deps: GraphDeps, messages: list[BaseMessage], fonts: list[str], step: str
) -> TemplateSpec | None:
    """Une demande, puis deux re-demandes au plus avec les défauts ; `None` s'il en reste."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    for ask in range(1, MAX_SPEC_ASKS + 1):
        found = await structured_call(
            model,
            TemplateSpec,
            messages,
            agent=AGENT,
            step=f"{step}-{ask}",
            intent="je décris le design de ton CV" if ask == 1 else "je corrige la description",
        )
        problems = template_problems(found, fonts)
        if not problems:
            return found
        # Le nombre seulement : un défaut cite une police, peut-être lue dans le PDF (17.2).
        logger.info(
            "Description refusée : session %s, %d défaut(s)", deps.session_id, len(problems)
        )
        messages = [
            *messages,
            AIMessage(found.model_dump_json()),
            HumanMessage(spec_retry(problems)),
        ]
    return None


def make_draft(deps: GraphDeps) -> Node:
    @node_timeout(VISION_TIMEOUT_S)
    async def draft(state: CvCaptureState) -> CvCaptureState:
        view = await _view(deps, state)
        width, height = view.page_size
        prompt = render_prompt(
            AGENT,
            mode="draft",
            page_width=f"{width:g}",
            page_height=f"{height:g}",
            page_count=view.page_count,
            fonts=", ".join(view.available_fonts),
            chosen=", ".join(dict.fromkeys(font.family for font in view.fonts)),
            blocks=untrusted(view.blocks_summary, "cv"),
        )
        messages: list[BaseMessage] = [
            SystemMessage(prompt),
            image_message(DRAFT_REQUEST, view.pages_png),
        ]
        spec = await ask_spec(deps, messages, view.available_fonts, "design")
        if spec is None:
            template_id = str(state["template_id"])
            raise await _failed(deps, template_id, "template_spec_invalid", NO_SPEC, 502)
        return {"spec": spec.model_dump(mode="json")}

    return draft


def compared(original: list[bytes], render: list[bytes]) -> tuple[str, list[bytes]]:
    """Original et rendu page à page (`MAX_IMAGES` au plus), et la légende des images."""
    labelled: list[tuple[str, bytes]] = []
    for page in range(max(len(original), len(render))):
        if page < len(original):
            labelled.append((f"original, page {page + 1}", original[page]))
        if page < len(render):
            labelled.append((f"rendu, page {page + 1}", render[page]))
    kept = labelled[:MAX_IMAGES]
    legend = "Images, dans l'ordre : " + " ; ".join(label for label, _ in kept) + "."
    return legend, [png for _, png in kept]


def make_fix(deps: GraphDeps) -> Node:
    @node_timeout(VISION_TIMEOUT_S)
    async def fix(state: CvCaptureState) -> CvCaptureState:
        template_id, pass_no = str(state["template_id"]), state["pass_no"]
        view = await _view(deps, state)
        done = await deps.ports.cv_templates.read_pass(deps.user_id, template_id, pass_no)
        instruction = state.get("instruction") if state.get("adjustments", 0) else None
        prompt = render_prompt(
            AGENT,
            mode="fix",
            spec=TemplateSpec.model_validate(state["spec"]).model_dump_json(indent=1),
            pass_no=pass_no,
            score=done.score,
            hints=describe(done.similarity) if done.score < TARGET_SCORE else "",
            instruction=untrusted(instruction, "consigne de January") if instruction else "",
            fonts=", ".join(view.available_fonts),
        )
        legend, images = compared(view.pages_png, done.render_png)
        messages: list[BaseMessage] = [
            SystemMessage(prompt),
            image_message(f"{FIX_REQUEST}\n{legend}", images),
        ]
        spec = await ask_spec(deps, messages, view.available_fonts, f"correction-{pass_no}")
        if spec is None:
            emit(
                "agent.message",
                {
                    "message_id": f"{AGENT}-correction-{pass_no}-{state.get('adjustments', 0)}",
                    "text": "Je n'ai pas su corriger la description : le modèle reste tel quel.",
                },
                agent=AGENT,
            )
            return {"stalled": True}
        return {"spec": spec.model_dump(mode="json"), "stalled": False}

    return fix

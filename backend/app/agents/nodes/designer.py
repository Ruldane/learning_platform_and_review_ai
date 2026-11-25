"""The Layout designer (vision, D125): flow `cv_capture`, `design` mode. It sees the CV pages.

`sample`: the demonstration content. CV with selectable text: the model copies it
(`CvContent`, images and blocks), each text absent from the CV is requested again once then
removed; scanned CV: the content of the validated profile (`sample_fallback`), otherwise a
readable failure.
`draft`: the description of the design (`TemplateSpec`); its defects (`template_problems`) are
requested again twice at most, then the capture fails readably.
`fix`: a corrected description, from the current description, the score gaps (`describe`, only
under `TARGET_SCORE`), the original and rendered images, and January's instruction if there is
one; without a valid description (defects after the re-requests, or invalid structured output),
the current description is kept (`stalled`) and the question is asked.

Logs: identifiers and numbers, never a text, an image or a font of the CV (17.2)."""

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
SAMPLE_REQUEST = "Transcribe the contents of this CV verbatim."
DRAFT_REQUEST = "Describe this CV's design."
FIX_REQUEST = "Revise the description so the render better matches the original."
MAX_SAMPLE_ASKS = 2  # one request, then one re-request with the texts absent from the CV
MAX_SPEC_ASKS = 3  # one request, then two re-requests with the defects
VISION_TIMEOUT_S = 600  # structured outputs with images, and their re-requests
NO_SAMPLE = "For a scanned CV, approve your master profile and then restart template capture."
NO_SPEC = "The Layout Designer couldn't describe this CV. Restart template capture."
STRUCTURED_INVALID = "structured_output_invalid"  # code of `structured_call` after its retries

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CvCaptureState) -> CvCaptureState: ...


async def _failed(
    deps: GraphDeps, template_id: str, code: str, reason: str, status: int
) -> AppError:
    """The template goes to `failed` (idempotent) before the session fails: never stuck in
    "capture" forever."""
    await deps.ports.cv_templates.finish(deps.user_id, template_id, "failed", reason)
    return AppError(code, reason, status)


async def _view(deps: GraphDeps, state: CvCaptureState) -> OriginalView:
    """Reread by the port (idempotent): the images never go through the state."""
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
            intent="Transcribing your CV" if ask == 1 else "Correcting the transcription",
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
            "Demonstration content: session %s, template %s, %d section(s), %d text(s) removed",
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
    """One request, then two re-requests at most with the defects; `None` if some remain."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    for ask in range(1, MAX_SPEC_ASKS + 1):
        found = await structured_call(
            model,
            TemplateSpec,
            messages,
            agent=AGENT,
            step=f"{step}-{ask}",
            intent="Describing your CV's design" if ask == 1 else "Revising the description",
        )
        problems = template_problems(found, fonts)
        if not problems:
            return found
        # The number only: a defect quotes a font, possibly read from the PDF (17.2).
        logger.info("Description refused: session %s, %d defect(s)", deps.session_id, len(problems))
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
    """Original and render page by page (`MAX_IMAGES` at most), and the image caption."""
    labelled: list[tuple[str, bytes]] = []
    for page in range(max(len(original), len(render))):
        if page < len(original):
            labelled.append((f"original, page {page + 1}", original[page]))
        if page < len(render):
            labelled.append((f"rendu, page {page + 1}", render[page]))
    kept = labelled[:MAX_IMAGES]
    legend = "Images, in order: " + "; ".join(label for label, _ in kept) + "."
    return legend, [png for _, png in kept]


async def _correction(
    deps: GraphDeps, messages: list[BaseMessage], fonts: list[str], step: str
) -> TemplateSpec | None:
    """`ask_spec`, where an invalid structured output (GLM: truncated JSON) counts as "no valid
    description": a rendered pass exists, the question can still be asked (review 6.9, I2)."""
    try:
        return await ask_spec(deps, messages, fonts, step)
    except AppError as exc:
        if exc.code != STRUCTURED_INVALID:
            raise
        logger.info("Correction without a valid output: session %s", deps.session_id)
        return None


def make_fix(deps: GraphDeps) -> Node:
    @node_timeout(VISION_TIMEOUT_S)
    async def fix(state: CvCaptureState) -> CvCaptureState:
        template_id, pass_no = str(state["template_id"]), state["pass_no"]
        view = await _view(deps, state)
        adjusting = state.get("adjustments", 0) > 0
        # An adjustment restarts from the kept pass (the best one: 69, 78, 69 restarts from 78),
        # with its description; a checkpoint from before `kept_spec` restarts from the last pass.
        from_kept = adjusting and "kept_spec" in state and "kept_pass" in state
        base_no = state["kept_pass"] if from_kept else pass_no
        base_spec = state["kept_spec"] if from_kept else state["spec"]
        done = await deps.ports.cv_templates.read_pass(deps.user_id, template_id, base_no)
        instruction = state.get("instruction") if adjusting else None
        prompt = render_prompt(
            AGENT,
            mode="fix",
            spec=TemplateSpec.model_validate(base_spec).model_dump_json(indent=1),
            pass_no=base_no,
            score=done.score,
            hints=describe(done.similarity) if done.score < TARGET_SCORE else "",
            instruction=untrusted(instruction, "January's instruction") if instruction else "",
            fonts=", ".join(view.available_fonts),
        )
        legend, images = compared(view.pages_png, done.render_png)
        messages: list[BaseMessage] = [
            SystemMessage(prompt),
            image_message(f"{FIX_REQUEST}\n{legend}", images),
        ]
        spec = await _correction(deps, messages, view.available_fonts, f"correction-{pass_no}")
        if spec is None:
            emit(
                "agent.message",
                {
                    "message_id": f"{AGENT}-correction-{pass_no}-{state.get('adjustments', 0)}",
                    "text": "The description could not be adjusted. The template is unchanged.",
                },
                agent=AGENT,
            )
            return {"stalled": True}
        return {"spec": spec.model_dump(mode="json"), "stalled": False}

    return fix

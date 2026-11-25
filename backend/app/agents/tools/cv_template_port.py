"""Port for CV templates (D125): what the layout designer (`cv_capture`, `design` mode) borrows
from the `cv` feature (`AgentCvTemplateStore`, 6.10), without importing it (contract 6).

Each write is **idempotent** (SPEC 9.4): `prepare` per template, `render_pass` per
`(template, pass)` (a pass already rendered is reread, never rendered twice), `finish` per
template. `read_pass` rereads a stored pass without any rendering: the `fix` node takes the images
of the render from it, which the graph state does not keep (the checkpoints stay light).

The text and images of a CV, the font names read from the PDF are personal or untrusted data
personnelles : ni journal, ni message d'erreur."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents.tools.cv_schema import CvContent
from app.agents.tools.template_schema import TemplateSpec
from app.agents.tools.template_similarity import Similarity
from app.core.errors import AppError
from app.providers.fonts.catalog import FontChoice

TemplateOutcome = Literal["ready", "failed"]


@dataclass(frozen=True)
class OriginalView:
    """The original CV as the layout designer sees it. `blocks_summary`: one line per block,
    "x,y,w,h | font | size | color | bold | text"; `fonts`: free fonts chosen for those of the PDF
    (`FontChoice`); `available_fonts`: families a `TemplateSpec` may cite;
    `original_text`: visible text in stream order (check of copied lines)."""

    template_id: str
    page_count: int
    page_size: tuple[float, float]  # width, height in points
    selectable: bool  # false: scanned CV, no text
    pages_png: list[bytes]
    blocks_summary: str
    fonts: list[FontChoice]
    available_fonts: list[str]
    original_text: str


@dataclass(frozen=True)
class PassResult:
    pass_no: int
    score: int
    similarity: Similarity
    render_png: list[bytes]


def keeps_pass(adjusted: bool, score: int, kept_score: int | None) -> bool:
    """Does the rendered pass become the template's kept pass? Among the automatic passes,
    the best wins (tie: the most recent): 69, 78, 69 keeps pass 2. An adjustment pass
    follows January's instruction, which the score does not see: it always replaces.
    Common rule for the real port, the fake and the graph: the score shown is that of the
    kept pass."""
    return kept_score is None or adjusted or score >= kept_score


class CvTemplateStore(Protocol):
    async def prepare(self, user_id: str, template_id: str) -> OriginalView:
        """Idempotent: layout (6.3), images stored, fonts chosen and downloaded,
        deviations noted; reread as is afterwards. Missing template or another's: 404."""
        ...

    async def sample_fallback(self, user_id: str) -> CvContent | None:
        """Demonstration content from the validated profile (scanned CV); `None` without one."""
        ...

    async def render_pass(
        self,
        user_id: str,
        template_id: str,
        pass_no: int,
        spec: TemplateSpec,
        content: CvContent,
        adjusted: bool = False,
    ) -> PassResult:
        """Idempotent per `(template_id, pass_no)`: pass already rendered -> reread without a new
        rendering; otherwise `cv_document`, `html_to_pdf`, extraction of the render, `similarity`,
        storing (spec, html, css, score, zones, images) of the pass only if `keeps_pass`; the pass
        stays in the pass journal in all cases."""
        ...

    async def read_pass(self, user_id: str, template_id: str, pass_no: int) -> PassResult:
        """A pass already stored, reread without any rendering; 404 if it does not exist."""
        ...

    async def finish(
        self, user_id: str, template_id: str, status: TemplateOutcome, reason: str | None
    ) -> None:
        """`ready`: the kept pass (`keeps_pass`) becomes the template, active if no
        other is; `failed`: `reason` (a French sentence, no CV data) stored.
        Idempotent; a `failed` template no longer becomes `ready` (409 `template_not_capturing`)."""
        ...


def cv_templates_unavailable() -> AppError:
    return AppError(
        "cv_templates_unavailable", "CV templates are unavailable in this runtime.", 503
    )


class _NoCvTemplates:
    """Engine default value (tests, starts without the feature)."""

    async def prepare(self, user_id: str, template_id: str) -> OriginalView:
        raise cv_templates_unavailable()

    async def sample_fallback(self, user_id: str) -> CvContent | None:
        raise cv_templates_unavailable()

    async def render_pass(
        self,
        user_id: str,
        template_id: str,
        pass_no: int,
        spec: TemplateSpec,
        content: CvContent,
        adjusted: bool = False,
    ) -> PassResult:
        raise cv_templates_unavailable()

    async def read_pass(self, user_id: str, template_id: str, pass_no: int) -> PassResult:
        raise cv_templates_unavailable()

    async def finish(
        self, user_id: str, template_id: str, status: TemplateOutcome, reason: str | None
    ) -> None:
        raise cv_templates_unavailable()


NO_CV_TEMPLATES: CvTemplateStore = _NoCvTemplates()

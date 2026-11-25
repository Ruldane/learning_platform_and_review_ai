"""Exporting the program as an A4 PDF (SPEC 3.4, D89): template `program/program.html.j2`
(automatic escaping of all titles, criteria and skills, coming from an agent or January), no
script, no remote resource. Rendered on demand: a few seconds of Gotenberg, not an agent job."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.program.schemas import ProgramOut
from app.features.program.service import programs
from app.features.program.service.ics import TASK_TYPE_LABELS
from app.providers.pdf.base import HtmlDocument, HtmlPdfRenderer, RenderFailed
from app.templates import render_template
from app.templates.assets import template_file

logger = logging.getLogger(__name__)

CSP = "default-src 'none'; style-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'"
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip


def _day(value: date) -> str:
    return f"{_DAYS[value.weekday()]} {value.day} {_MONTHS[value.month - 1]} {value.year}"


def _hours(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{rest} min"
    return f"{hours} h {rest} min" if rest else f"{hours} h"


def program_document(program: ProgramOut) -> HtmlDocument:
    index = render_template(
        "program/program.html.j2",
        program=program,
        csp=CSP,
        day=_day,
        hours=_hours,
        types=TASK_TYPE_LABELS,
    )
    return HtmlDocument(
        index_html=index,
        assets={"program.css": template_file("program/program.css").encode()},
        footer_html=template_file("lesson/footer.html"),
    )


async def program_pdf(renderer: HtmlPdfRenderer, program: ProgramOut) -> bytes:
    return await renderer.html_to_pdf(program_document(program))


async def export_program_pdf(
    db: AsyncSession, renderer: HtmlPdfRenderer, user_id: str, program_id: str
) -> bytes:
    """The user's program PDF (`program_not_found` otherwise). The read is closed before the
    render (up to 45 s); an impossible render becomes a readable 502 `render_failed`."""
    program = await programs.get_program(db, user_id, program_id)
    await db.commit()
    try:
        pdf = await program_pdf(renderer, program)
    except RenderFailed:
        raise AppError(
            "render_failed",
            "The program PDF could not be generated. Try again in a moment.",
            status_code=502,
        ) from None
    logger.info("Program PDF rendered (program %s, %d bytes)", program.id, len(pdf))
    return pdf

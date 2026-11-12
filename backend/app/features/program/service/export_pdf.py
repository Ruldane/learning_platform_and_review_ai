"""Export du programme en PDF A4 (SPEC 3.4, D89) : gabarit `program/program.html.j2` (échappement
automatique de tous les titres, critères et compétences, venus d'un agent ou de January), aucun
script, aucune ressource distante. Rendu à la demande : quelques secondes de Gotenberg, pas un
travail d'agent."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.program.schemas import ProgramOut
from app.features.program.service import programs
from app.providers.pdf.base import HtmlDocument, HtmlPdfRenderer, RenderFailed
from app.templates import render_template
from app.templates.assets import template_file

logger = logging.getLogger(__name__)

CSP = "default-src 'none'; style-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'"
_TYPES = {
    "lire": "Lire",
    "regarder": "Regarder",
    "pratiquer": "Pratiquer",
    "quiz": "Quiz",
    "projet": "Projet",
}
_DAYS = ("lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim.")
_MONTHS = (
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
)  # fmt: skip


def _day(value: date) -> str:
    return f"{_DAYS[value.weekday()]} {value.day} {_MONTHS[value.month - 1]} {value.year}"


def _hours(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest:02d}" if rest else f"{hours} h"


def program_document(program: ProgramOut) -> HtmlDocument:
    index = render_template(
        "program/program.html.j2", program=program, csp=CSP, day=_day, hours=_hours, types=_TYPES
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
    """PDF du programme de l'utilisateur (`program_not_found` sinon). La lecture est close avant
    le rendu (jusqu'à 45 s) ; un rendu impossible devient une 502 `render_failed` lisible."""
    program = await programs.get_program(db, user_id, program_id)
    await db.commit()
    try:
        pdf = await program_pdf(renderer, program)
    except RenderFailed:
        raise AppError(
            "render_failed",
            "PDF du programme impossible pour le moment : réessaie dans un instant.",
            status_code=502,
        ) from None
    logger.info("PDF du programme rendu (programme %s, %d octets)", program.id, len(pdf))
    return pdf

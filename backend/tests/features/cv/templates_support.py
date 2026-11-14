"""Matériel des tests des gabarits de CV (D126) : un fichier envoyé comme par la route, une capture
lancée par le service (lanceur factice, aucune session ne tourne), la ligne du gabarit relue, un
extracteur de mise en page qui compte ses appels."""

import io
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import update
from starlette.datastructures import Headers

from app.agents.tools.template_schema import TemplateSpec
from app.db.models.agents import AgentSession
from app.db.models.career import CvTemplate
from app.features.cv.repository import TemplateRepository
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.templates_create import create_template
from app.providers.pdf.base import PdfLayout, PdfLayoutExtractor
from scripts.sample_cv import make_cv_pdf
from tests.support.cv_template import spec as cv_spec

ME = "moi"
SECRET_NAME = "Modèle très secret de Camille"


def upload(data: bytes, filename: str = "CV_Camille_Exemple.pdf") -> UploadFile:
    headers = Headers({"content-type": "application/pdf"})
    return UploadFile(file=io.BytesIO(data), filename=filename, headers=headers)


async def capture(rt: CvRuntime, pdf: bytes | None = None, user_id: str = ME) -> str:
    """Un gabarit en capture (le PDF rangé, sa mise en page gardée) ; rend son id."""
    created = await create_template(
        rt, user_id, name=SECRET_NAME, file=upload(pdf or make_cv_pdf()), document_id=None
    )
    return created.template_id


async def end_sessions(rt: CvRuntime, status: str = "completed") -> None:
    """Les sessions du lanceur factice se terminent (comme le moteur après `finish`)."""
    async with rt.session_factory() as db:
        await db.execute(update(AgentSession).values(status=status))
        await db.commit()


async def template_row(rt: CvRuntime, template_id: str, user_id: str = ME) -> CvTemplate:
    async with rt.session_factory() as db:
        row = await TemplateRepository(db, user_id).get(template_id)
    assert row is not None
    return row


def liberation_spec() -> TemplateSpec:
    """La description fictive, en Liberation Sans (toujours citable)."""
    spec = cv_spec()
    fonts = spec.fonts.model_copy(update={"body": "Liberation Sans", "heading": "Liberation Sans"})
    return spec.model_copy(update={"fonts": fonts})


@dataclass
class CountingLayout:
    inner: PdfLayoutExtractor
    calls: int = 0

    async def extract_layout(self, data: bytes) -> PdfLayout:
        self.calls += 1
        return await self.inner.extract_layout(data)

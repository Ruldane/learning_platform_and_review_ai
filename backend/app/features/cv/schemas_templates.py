"""Schémas des gabarits de CV (SPEC 5.2, 14.2 ; D126). Un gabarit = un CV d'origine (rangé dans
la mémoire), ses images, la description du Maquettiste, le HTML et le CSS écrits par le code, son
score et ses passes ; un seul actif. Aucun nom de police lu dans le PDF n'est rendu : `fonts`
donne les familles libres employées, `font_gaps` dit chaque écart en phrase."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.db.models.career import TemplateStatus

PageKind = Literal["original", "render"]


class TemplateCreated(BaseModel):
    """Capture du design lancée : le gabarit (`capturing`) et sa session `cv_capture`."""

    template_id: str
    session_id: str


class TemplateSummaryOut(BaseModel):
    """`score` : ressemblance de la passe courante (0 à 100), `None` avant la première passe ;
    `passes` : passes rendues."""

    id: str
    name: str
    status: TemplateStatus
    active: bool
    score: int | None
    passes: int
    page_count: int
    created_at: datetime


class FontUseOut(BaseModel):
    """Police libre employée pour un rôle ; `substitute` : elle remplace celle du PDF."""

    role: Literal["body", "heading"]
    family: str
    substitute: bool


class ZoneDiffOut(BaseModel):
    """Part d'encre (0 à 1) d'une zone de la page (`haut`, `milieu`, `bas`, `gauche`, `droite`)
    dans l'original et dans le rendu de la passe courante."""

    zone: str
    original: float
    render: float


class TemplateOut(TemplateSummaryOut):
    """`selectable` : faux pour un CV scanné ; `session_id` : la capture du design ;
    `failure_reason` : phrase française d'un échec (sans donnée du CV)."""

    selectable: bool
    fonts: list[FontUseOut]
    font_gaps: list[str]
    zones: list[ZoneDiffOut]
    session_id: str | None
    failure_reason: str | None

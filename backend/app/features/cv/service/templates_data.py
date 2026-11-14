"""Ce qu'un gabarit garde de son CV d'origine et de ses passes (D126), sous une forme relisible
sans nouvelle extraction : géométrie des pages (cadres des blocs visibles, pour `similarity`),
blocs résumés pour le Maquettiste (familles libres, jamais le nom de police lu dans le PDF),
texte visible dans l'ordre du flux, ressemblance d'une passe. Et le contenu de démonstration tiré
du profil maître validé (CV scanné). Module pur : ni base, ni stockage."""

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from app.agents.tools.cv_schema import (
    CvContent,
    CvEntry,
    CvLine,
    CvSection,
    MasterProfileData,
    SectionKey,
)
from app.agents.tools.template_similarity import Similarity, ZoneDiff, ZoneMatch
from app.core.errors import AppError
from app.providers.fonts.catalog import choose_font
from app.providers.pdf.base import PageLayout, PdfLayout, TextBlock

MAX_SUMMARY_LINES = 400
MAX_BLOCK_CHARS = 200


def template_not_found() -> AppError:
    return AppError("template_not_found", "Modèle de CV introuvable.", 404)


def _visible(page: PageLayout) -> list[TextBlock]:
    return [b for b in page.blocks if not b.invisible and b.text.strip()]


def geometry(layout: PdfLayout) -> list[dict[str, Any]]:
    """Par page : taille et cadres `[x0, top, x1, bottom]` des blocs visibles (sans texte)."""
    return [
        {
            "width_pt": page.width_pt,
            "height_pt": page.height_pt,
            "boxes": [[b.x0, b.top, b.x1, b.bottom] for b in _visible(page)],
        }
        for page in layout.pages
    ]


def original_pages(pages: Sequence[dict[str, Any]], images: Sequence[bytes]) -> list[PageLayout]:
    """Les pages d'origine telles que `similarity` les lit : cadres visibles et image."""
    return [
        PageLayout(
            width_pt=float(page["width_pt"]),
            height_pt=float(page["height_pt"]),
            blocks=[
                TextBlock("", x0, top, x1, bottom, "", 0.0, "#000000", False, False)
                for x0, top, x1, bottom in page["boxes"]
            ],
            image_png=image,
            stream_text="",
        )
        for page, image in zip(pages, images, strict=True)
    ]


def _line(block: TextBlock) -> str:
    box = ",".join(
        str(round(v)) for v in (block.x0, block.top, block.x1 - block.x0, block.bottom - block.top)
    )
    family = choose_font(block.font).family
    bold = "oui" if block.bold else "non"
    text = " ".join(block.text.split())[:MAX_BLOCK_CHARS]
    return f"{box} | {family} | {block.size:g} | {block.color} | {bold} | {text}"


def blocks_summary(layout: PdfLayout) -> str:
    """« x,y,l,h | police | taille | couleur | gras | texte » par bloc visible ; la police est la
    famille libre retenue ; une ligne « Page n » sépare les pages ; `MAX_SUMMARY_LINES` au plus."""
    lines: list[str] = []
    for number, page in enumerate(layout.pages, start=1):
        if len(layout.pages) > 1:
            lines.append(f"Page {number}")
        lines += [_line(block) for block in _visible(page)]
    return "\n".join(lines[:MAX_SUMMARY_LINES])


def visible_text(layout: PdfLayout) -> str:
    """Texte visible, blocs dans l'ordre du flux, une page par paragraphe."""
    return "\n\n".join("\n".join(b.text for b in _visible(page)) for page in layout.pages)


def similarity_to_json(sim: Similarity) -> dict[str, Any]:
    return asdict(sim)


def similarity_from_json(data: dict[str, Any]) -> Similarity:
    return Similarity(
        **{
            **data,
            "zones": [ZoneDiff(**zone) for zone in data.get("zones", [])],
            "matches": [ZoneMatch(**match) for match in data.get("matches", [])],
            "shifts": dict(data.get("shifts", {})),
        }
    )


def _period(start: str | None, end: str | None) -> str | None:
    return " – ".join(part for part in (start, end) if part) or None


def _lines(texts: Sequence[str]) -> list[CvLine]:
    return [CvLine(text=text) for text in texts if text.strip()]


def _sections(profile: MasterProfileData) -> list[CvSection]:
    sections: list[CvSection] = []
    if profile.summary is not None:
        sections.append(
            CvSection(key="summary", title="Profil", items=_lines([profile.summary.text]))
        )
    experiences = [
        CvEntry(
            heading=f"{x.role} — {x.company}",
            subheading=x.location,
            dates=_period(x.start, x.end),
            lines=_lines([line.text for line in x.achievements]),
        )
        for x in profile.experiences
    ]
    education = [
        CvEntry(
            heading=f"{e.degree} — {e.school}",
            dates=_period(e.start, e.end),
            lines=_lines([line.text for line in e.details]),
        )
        for e in profile.education
    ]
    skills = _lines([skill.name for skill in profile.skills])
    languages = _lines(
        [" ".join(filter(None, (lang.name, lang.level))) for lang in profile.languages]
    )
    groups: list[tuple[SectionKey, str, list[CvEntry], list[CvLine]]] = [
        ("experience", "Expériences", experiences, []),
        ("education", "Formation", education, []),
        ("skills", "Compétences", [], skills),
        ("languages", "Langues", [], languages),
    ]
    for key, title, entries, items in groups:
        if entries or items:
            sections.append(CvSection(key=key, title=title, entries=entries, items=items))
    return sections


def profile_content(profile: MasterProfileData) -> CvContent:
    """Contenu de démonstration d'un CV scanné : le profil validé, sans `fact_ids` (une
    démonstration ne s'adosse à aucun fait)."""
    identity = profile.identity
    contact = [v for v in (identity.email, identity.phone, identity.location) if v]
    headline = profile.title.text if profile.title is not None else identity.headline
    return CvContent(
        name=identity.name, headline=headline, contact=contact, sections=_sections(profile)
    )

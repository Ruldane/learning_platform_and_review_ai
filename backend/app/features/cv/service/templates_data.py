"""What a template keeps from its original CV and its passes (D126), in a form that can be
reread without new extraction: page geometry (frames of the visible blocks, for `similarity`),
blocks summarized for the layout designer (free families, never the font name read from the
PDF), visible text in flow order, similarity of a pass. And the demo content taken from the
validated master profile (scanned CV). Pure module: no database, no storage."""

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
from app.agents.tools.template_grids import zone_code
from app.agents.tools.template_similarity import Similarity, ZoneDiff, ZoneMatch
from app.core.errors import AppError
from app.providers.fonts.catalog import choose_font
from app.providers.pdf.base import PageLayout, PdfLayout, TextBlock

MAX_SUMMARY_LINES = 400
MAX_BLOCK_CHARS = 200


def template_not_found() -> AppError:
    return AppError("template_not_found", "CV template not found.", 404)


def _visible(page: PageLayout) -> list[TextBlock]:
    return [b for b in page.blocks if not b.invisible and b.text.strip()]


def geometry(layout: PdfLayout) -> list[dict[str, Any]]:
    """Per page: size and frames `[x0, top, x1, bottom]` of the visible blocks (no text)."""
    return [
        {
            "width_pt": page.width_pt,
            "height_pt": page.height_pt,
            "boxes": [[b.x0, b.top, b.x1, b.bottom] for b in _visible(page)],
        }
        for page in layout.pages
    ]


def original_pages(pages: Sequence[dict[str, Any]], images: Sequence[bytes]) -> list[PageLayout]:
    """The original pages as `similarity` reads them: visible frames and image."""
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
    bold = "yes" if block.bold else "no"
    text = " ".join(block.text.split())[:MAX_BLOCK_CHARS]
    return f"{box} | {family} | {block.size:g} | {block.color} | {bold} | {text}"


def blocks_summary(layout: PdfLayout) -> str:
    """One line per visible block: "x,y,w,h | font | size | color | bold | text". The font is the
    free family kept; a "Page n" line separates the pages; at most `MAX_SUMMARY_LINES` lines."""
    lines: list[str] = []
    for number, page in enumerate(layout.pages, start=1):
        if len(layout.pages) > 1:
            lines.append(f"Page {number}")
        lines += [_line(block) for block in _visible(page)]
    return "\n".join(lines[:MAX_SUMMARY_LINES])


def visible_text(layout: PdfLayout) -> str:
    """Visible text, blocks in flow order, one page per paragraph."""
    return "\n\n".join("\n".join(b.text for b in _visible(page)) for page in layout.pages)


def similarity_to_json(sim: Similarity) -> dict[str, Any]:
    return asdict(sim)


def similarity_from_json(data: dict[str, Any]) -> Similarity:
    return Similarity(
        **{
            **data,
            "zones": [
                ZoneDiff(**{**entry, "zone": zone_code(entry["zone"])})
                for entry in data.get("zones", [])
            ],
            "matches": [
                ZoneMatch(**{**entry, "zone": zone_code(entry["zone"])})
                for entry in data.get("matches", [])
            ],
            "shifts": {zone_code(zone): shift for zone, shift in data.get("shifts", {}).items()},
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
            CvSection(key="summary", title="Profile", items=_lines([profile.summary.text]))
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
        ("experience", "Experience", experiences, []),
        ("education", "Education", education, []),
        ("skills", "Skills", [], skills),
        ("languages", "Languages", [], languages),
    ]
    for key, title, entries, items in groups:
        if entries or items:
            sections.append(CvSection(key=key, title=title, entries=entries, items=items))
    return sections


def profile_content(profile: MasterProfileData) -> CvContent:
    """Demo content of a scanned CV: the validated profile, without `fact_ids` (a demo relies on
    no fact)."""
    identity = profile.identity
    contact = [v for v in (identity.email, identity.phone, identity.location) if v]
    headline = profile.title.text if profile.title is not None else identity.headline
    return CvContent(
        name=identity.name, headline=headline, contact=contact, sections=_sections(profile)
    )

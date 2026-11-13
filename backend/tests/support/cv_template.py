"""Spec et contenu fictifs d'un CV (Camille Exemple, `scripts.sample_cv.CV_FACTS`) pour les tests
du gabarit, des contrôles de lisibilité et du resserrement (6.4), réutilisables en 6.9 à 6.14."""

from typing import Any

from app.agents.tools.cv_schema import CvContent, CvEntry, CvLine, CvSection
from app.agents.tools.template_schema import ColumnSpec, FontSpec, PageSpec, TemplateSpec
from scripts.sample_cv import CV_FACTS, PAGE_SIZES


def page(name: str = "A4") -> PageSpec:
    width, height = PAGE_SIZES[name]
    return PageSpec(width_pt=width, height_pt=height, margins_mm=(12, 12, 12, 12))


def letter() -> PageSpec:
    return page("Letter")


def two_columns() -> list[ColumnSpec]:
    return [
        ColumnSpec(
            width_pct=32,
            background="#eeeeee",
            sections=["identity", "skills", "languages"],
        ),
        ColumnSpec(width_pct=68, sections=["summary", "experience", "education"]),
    ]


def spec(**changes: Any) -> TemplateSpec:
    """Spec valide (deux colonnes, A4) ; `changes` remplace des champs de premier niveau."""
    values: dict[str, Any] = {
        "page": page(),
        "columns": two_columns(),
        "fonts": FontSpec(
            body="Lato", heading="Lato", body_pt=10, heading_pt=12, name_pt=22, line_height=1.3
        ),
        "accent": "#21549a",
        "text": "#222222",
        "muted": "#666666",
        "header_band": None,
        "section_title": "underline",
        "uppercase_titles": False,
        "dates": "right",
        "bullets": "dot",
        "gap_mm": 4,
    }
    values.update(changes)
    return TemplateSpec(**values)


def _line(text: str, fact: str) -> CvLine:
    return CvLine(text=text, fact_ids=[fact])


def content(lines: list[str] | None = None, **changes: Any) -> CvContent:
    """Contenu fictif complet ; `lines` remplace les puces de la première expérience."""
    facts = CV_FACTS
    values: dict[str, Any] = {
        "name": facts["name"],
        "headline": facts["title"],
        "contact": [facts["email"], facts["phone"], f"{facts['city']}, France"],
        "sections": _sections(lines),
    }
    values.update(changes)
    return CvContent(**values)


def _sections(lines: list[str] | None) -> list[CvSection]:
    facts = CV_FACTS
    bullets = lines or [
        "Conçu un assistant interne avec LangGraph pour le support",
        f"Réduit de {facts['metric_1']} le temps de traitement des demandes",
    ]
    return [
        CvSection(
            key="summary",
            title="Profil",
            items=[_line("Cinq ans d'expérience en données et en agents.", "s1")],
        ),
        CvSection(
            key="experience",
            title="Expérience professionnelle",
            entries=[
                CvEntry(
                    heading=f"{facts['role_1']} — {facts['company_1']}",
                    dates=facts["period_1"],
                    subheading=facts["city"],
                    lines=[_line(text, "x1a1") for text in bullets],
                    fact_id="x1",
                ),
                CvEntry(
                    heading=f"{facts['role_2']} — {facts['company_2']}",
                    dates=facts["period_2"],
                    lines=[_line("Automatisé le contrôle de 12 000 factures par mois", "x2a1")],
                    fact_id="x2",
                ),
            ],
        ),
        CvSection(
            key="education",
            title="Formation",
            entries=[CvEntry(heading=f"{facts['degree']} — {facts['school']}", dates="2020")],
        ),
        CvSection(
            key="skills",
            title="Compétences",
            items=[_line(skill, "c1") for skill in ("Python", "FastAPI", "Docker")],
        ),
        CvSection(key="languages", title="Langues", items=[_line(facts["language"], "l1")]),
    ]

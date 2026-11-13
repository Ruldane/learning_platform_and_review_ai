"""Lisibilité d'un CV par une machine (SPEC 5.3 étape 4, 5.4 ; D120) : cinq contrôles sur la mise
en page extraite du PDF (`PdfLayout`) et le contenu attendu (`CvContent`). Aucune garantie de
passage n'est promise. Les `detail` sont des phrases françaises faites de nombres et de noms de
section du code, **jamais** de texte du CV (donnée personnelle, 17.2)."""

import re
from collections.abc import Iterator, Sequence

from app.agents.tools.cv_schema import CvContent, CvSection, SectionKey
from app.agents.tools.posting_schema import Keyword, contains_term, normalize_term
from app.features.cv.service.indicators import AtsCheck
from app.providers.pdf.base import PdfLayout, TextBlock

STANDARD_HEADINGS: dict[SectionKey, tuple[str, ...]] = {
    "summary": (
        "Profil", "Profil professionnel", "Résumé", "Résumé professionnel", "À propos",
        "Summary", "Professional summary", "Profile", "About", "About me",
    ),
    "experience": (
        "Expérience professionnelle", "Expérience", "Parcours professionnel",
        "Expériences professionnelles", "Experience", "Work experience",
        "Professional experience", "Employment history", "Work history",
    ),
    "education": (
        "Formation", "Formations", "Éducation", "Diplômes", "Études", "Parcours académique",
        "Education", "Academic background", "Qualifications",
    ),
    "skills": (
        "Compétences", "Compétences techniques", "Savoir-faire", "Outils",
        "Skills", "Technical skills", "Core skills", "Tools",
    ),
    "projects": ("Projets", "Projets personnels", "Réalisations", "Projects", "Personal projects"),
    "languages": ("Langues", "Languages"),
    "links": ("Liens", "Sites", "En ligne", "Links", "Online", "Portfolio"),
}  # fmt: skip
_SECTION_NAMES: dict[SectionKey, str] = {
    "summary": "profil",
    "experience": "expérience",
    "education": "formation",
    "skills": "compétences",
    "projects": "projets",
    "languages": "langues",
    "links": "liens",
}
MIN_BODY_PT = 10.0
BODY_SHARE = 0.95
EDGE_BAND = 0.04
READING_SHARE = 0.9
LINE_START_CHARS = 30  # début normalisé d'une ligne cherché dans le flux
_SIZE_TOLERANCE = 0.05
_MIN_PHONE_DIGITS = 8
_NON_DIGIT = re.compile(r"\D")


def _visible(layout: PdfLayout) -> Iterator[tuple[float, TextBlock]]:
    """(hauteur de la page, bloc) de chaque bloc visible."""
    for page in layout.pages:
        for block in page.blocks:
            if not block.invisible:
                yield page.height_pt, block


def _selectable(layout: PdfLayout) -> AtsCheck:
    hidden = sum(block.invisible for page in layout.pages for block in page.blocks)
    if not layout.selectable:
        detail = "Le texte n'est pas sélectionnable : un parseur ne lit rien (PDF scanné ?)."
    elif hidden:
        detail = f"{hidden} ligne(s) de texte invisible (couleur du fond ou taille minuscule)."
    else:
        detail = "Texte sélectionnable, aucun texte invisible."
    return AtsCheck("selectable_text", layout.selectable and not hidden, detail)


def _section_lines(section: CvSection) -> list[str]:
    lines: list[str] = []
    for entry in section.entries:
        lines += [entry.heading, entry.subheading or "", entry.dates or ""]
        lines += [line.text for line in entry.lines]
    lines += [item.text for item in section.items]
    return [start for line in lines if (start := normalize_term(line)[:LINE_START_CHARS].strip())]


def _title_positions(stream: str, sections: Sequence[CvSection]) -> list[tuple[int, int, int]]:
    """(début, fin, rang de la section) de la première occurrence de chaque intitulé trouvé
    dans le flux normalisé, triés par position."""
    found: list[tuple[int, int, int]] = []
    for rank, section in enumerate(sections):
        title = normalize_term(section.title)
        start = stream.find(f" {title} ") if title else -1
        if start >= 0:
            found.append((start, start + len(title) + 2, rank))
    return sorted(found)


def _reading_order(layout: PdfLayout, content: CvContent) -> AtsCheck:
    stream = f" {normalize_term(' '.join(page.stream_text for page in layout.pages))} "
    expected = [_section_lines(section) for section in content.sections]
    total = sum(len(lines) for lines in expected)
    positions = _title_positions(stream, content.sections)
    found = 0
    for index, (_start, end, rank) in enumerate(positions):
        stop = positions[index + 1][0] + 1 if index + 1 < len(positions) else len(stream)
        segment = stream[end - 1 : stop]
        found += sum(f" {line}" in segment for line in expected[rank])
    passed = total == 0 or found >= READING_SHARE * total
    detail = (
        f"{found} ligne(s) sur {total} lues dans leur section, dans l'ordre du texte du PDF."
        if total
        else "Aucune ligne à retrouver."
    )
    return AtsCheck("reading_order", passed, detail)


def _standard_headings(content: CvContent) -> AtsCheck:
    odd = [
        _SECTION_NAMES[section.key]
        for section in content.sections
        if normalize_term(section.title, plural=True)
        not in {normalize_term(h, plural=True) for h in STANDARD_HEADINGS[section.key]}
    ]
    total = len(content.sections)
    if odd:
        detail = f"Intitulé peu courant pour : {', '.join(odd)} ({total - len(odd)} sur {total})."
    else:
        detail = f"Intitulés standard ({total} sur {total})."
    return AtsCheck("standard_headings", not odd, detail)


def _contact_in_body(layout: PdfLayout, content: CvContent) -> AtsCheck:
    emails = [normalize_term(value) for value in content.contact if "@" in value]
    phones = [
        digits
        for value in content.contact
        if "@" not in value and len(digits := _NON_DIGIT.sub("", value)) >= _MIN_PHONE_DIGITS
    ]
    found = False
    for height, block in _visible(layout):
        if block.top < EDGE_BAND * height or block.bottom > (1 - EDGE_BAND) * height:
            continue
        text, digits = f" {normalize_term(block.text)} ", _NON_DIGIT.sub("", block.text)
        if any(f" {email} " in text for email in emails if email) or any(
            phone in digits for phone in phones
        ):
            found = True
            break
    if not emails and not phones:
        detail = "Aucun email ni téléphone dans les coordonnées."
    elif found:
        detail = "Email ou téléphone lisible dans le corps de la page."
    else:
        detail = "Email et téléphone introuvables hors des bandes haute et basse de la page."
    return AtsCheck("contact_in_body", found, detail)


def _font_sizes(layout: PdfLayout) -> AtsCheck:
    total = large = 0
    for _height, block in _visible(layout):
        chars = sum(not ch.isspace() for ch in block.text)
        total += chars
        if block.size >= MIN_BODY_PT - _SIZE_TOLERANCE:
            large += chars
    share = large / total if total else 0.0
    percent = int(share * 100)
    detail = (
        f"{percent} % des caractères à {MIN_BODY_PT:g} pt ou plus."
        if total
        else "Aucun caractère visible."
    )
    return AtsCheck("font_sizes", total > 0 and share >= BODY_SHARE, detail)


def ats_checks(layout: PdfLayout, content: CvContent) -> list[AtsCheck]:
    """Les cinq contrôles, dans l'ordre de `AtsCheckId`."""
    return [
        _selectable(layout),
        _reading_order(layout, content),
        _standard_headings(content),
        _contact_in_body(layout, content),
        _font_sizes(layout),
    ]


def keyword_hits(text: str, keywords: Sequence[Keyword]) -> dict[str, bool]:
    """Terme → présent dans `text` (lui ou l'une de ses variantes, mots entiers ; casse, accents,
    ponctuation et pluriel simple ignorés, comme la couverture)."""
    return {
        keyword.term: any(
            contains_term(text, form, plural=True) for form in (keyword.term, *keyword.variants)
        )
        for keyword in keywords
    }

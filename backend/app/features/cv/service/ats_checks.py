"""Check CV readability from the PDF layout and expected content (SPEC 5.3, 5.4, D120).
Details use counts and standard section names to protect CV content (SPEC 17.2)."""

import re
from collections.abc import Iterator, Sequence

from app.agents.tools.cv_schema import CvContent, CvSection, SectionKey
from app.agents.tools.posting_schema import Keyword, contains_term, normalize_term
from app.features.cv.service.indicators import AtsCheck
from app.providers.pdf.base import PdfLayout, TextBlock

# French headings recognise CVs written in French (and rows stored before the switch to
# English); the English ones recognise the rest.
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
    "summary": "profile",
    "experience": "experience",
    "education": "education",
    "skills": "skills",
    "projects": "projects",
    "languages": "languages",
    "links": "links",
}
MIN_BODY_PT = 10.0
BODY_SHARE = 0.95
EDGE_BAND = 0.04
READING_SHARE = 0.9
LINE_START_CHARS = 30  # normalized start of a line searched for in the stream
_SIZE_TOLERANCE = 0.05
_MIN_PHONE_DIGITS = 8
_EDGE_SLACK_PT = 1.0  # overlap tolerated between two neighbouring lines
_NON_DIGIT = re.compile(r"\D")


def _visible(layout: PdfLayout) -> Iterator[tuple[float, TextBlock]]:
    """(page height, block) of each visible block."""
    for page in layout.pages:
        for block in page.blocks:
            if not block.invisible:
                yield page.height_pt, block


def _selectable(layout: PdfLayout) -> AtsCheck:
    hidden = sum(block.invisible for page in layout.pages for block in page.blocks)
    if not layout.selectable:
        detail = "The text is not selectable. The PDF may be a scan."
    elif hidden:
        detail = f"Hidden lines: {hidden}. The text is too small or matches the background."
    else:
        detail = "Text is selectable and all lines are visible."
    return AtsCheck("selectable_text", layout.selectable and not hidden, detail)


def _needles(section: CvSection) -> list[str]:
    """What is searched for from each line of the section in the normalized stream: its first
    `LINE_START_CHARS` characters (word start on the left), or the whole line between two word
    boundaries if it is shorter ("C" is not found in "Conçu")."""
    lines: list[str] = []
    for entry in section.entries:
        lines += [entry.heading, entry.subheading or "", entry.dates or ""]
        lines += [line.text for line in entry.lines]
    lines += [item.text for item in section.items]
    needles: list[str] = []
    for line in lines:
        text = normalize_term(line)
        if len(text) <= LINE_START_CHARS:
            needles += [f" {text} "] if text else []
        else:
            needles.append(f" {text[:LINE_START_CHARS].strip()}")
    return needles


def _stream_lines(layout: PdfLayout) -> tuple[str, list[tuple[int, str]]]:
    """Normalized stream (one space between two lines, one at the edges) and (start, text) of
    each of its non-empty lines."""
    stream = " "
    lines: list[tuple[int, str]] = []
    for page in layout.pages:
        for raw in page.stream_text.splitlines():
            text = normalize_term(raw)
            if text:
                lines.append((len(stream), text))
                stream += text + " "
    return stream, lines


def _title_positions(
    stream: str, lines: list[tuple[int, str]], sections: Sequence[CvSection]
) -> list[tuple[int, int, int]]:
    """(start, end, section rank) of each heading found, sorted by position: the heading is
    searched for as a **whole line** of the stream (an `<h2>` is a line on its own; "Project
    manager" does not place the "Projects" section); failing that, its first occurrence as
    whole words."""
    found: list[tuple[int, int, int]] = []
    taken: set[int] = set()
    for rank, section in enumerate(sections):
        title = normalize_term(section.title)
        if not title:
            continue
        start = next((s for s, text in lines if text == title and s not in taken), -1)
        if start < 0:
            start = stream.find(f" {title} ") + 1 if f" {title} " in stream else -1
        if start >= 0:
            taken.add(start)
            found.append((start, start + len(title), rank))
    return sorted(found)


def _reading_order(layout: PdfLayout, content: CvContent) -> AtsCheck:
    stream, lines = _stream_lines(layout)
    expected = [_needles(section) for section in content.sections]
    total = sum(len(needles) for needles in expected)
    positions = _title_positions(stream, lines, content.sections)
    found = 0
    for index, (_start, end, rank) in enumerate(positions):
        stop = positions[index + 1][0] if index + 1 < len(positions) else len(stream)
        segment = stream[end:stop]
        found += sum(needle in segment for needle in expected[rank])
    passed = total == 0 or found >= READING_SHARE * total
    detail = (
        f"{found} of {total} lines appear in their section in the PDF reading order."
        if total
        else "There are no lines to match."
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
        detail = f"Unusual headings for {', '.join(odd)} ({total - len(odd)} of {total} standard)."
    else:
        detail = f"Standard headings: {total} of {total}."
    return AtsCheck("standard_headings", not odd, detail)


def _in_body(block: TextBlock, visible: Sequence[TextBlock], height: float) -> bool:
    """The block is in the page body: outside the top and bottom bands (`EDGE_BAND`), or inside
    one of them but separated from the edge by another visible block (a contact under the name,
    in a banner stuck to the top of the page, follows the body flow; a lone line at the edge,
    alone between the edge and the rest, reads as a header or footer)."""
    if block.top < EDGE_BAND * height:
        return any(other.bottom <= block.top + _EDGE_SLACK_PT for other in visible)
    if block.bottom > (1 - EDGE_BAND) * height:
        return any(other.top >= block.bottom - _EDGE_SLACK_PT for other in visible)
    return True


def _contact_in_body(layout: PdfLayout, content: CvContent) -> AtsCheck:
    emails = [normalize_term(value) for value in content.contact if "@" in value]
    phones = [
        digits
        for value in content.contact
        if "@" not in value and len(digits := _NON_DIGIT.sub("", value)) >= _MIN_PHONE_DIGITS
    ]
    found = False
    for page in layout.pages:
        visible = [block for block in page.blocks if not block.invisible]
        for block in visible:
            text, digits = f" {normalize_term(block.text)} ", _NON_DIGIT.sub("", block.text)
            if not any(f" {email} " in text for email in emails if email) and not any(
                phone in digits for phone in phones
            ):
                continue
            if _in_body(block, visible, page.height_pt):
                found = True
                break
        if found:
            break
    if not emails and not phones:
        detail = "No email address or phone number was provided."
    elif found:
        detail = "The email address or phone number is readable in the page body."
    else:
        detail = "No email address or phone number was found in the page body."
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
        f"{percent}% of characters are {MIN_BODY_PT:g} pt or larger."
        if total
        else "No characters are visible."
    )
    return AtsCheck("font_sizes", total > 0 and share >= BODY_SHARE, detail)


def ats_checks(layout: PdfLayout, content: CvContent) -> list[AtsCheck]:
    """The five checks, in the order of `AtsCheckId`."""
    return [
        _selectable(layout),
        _reading_order(layout, content),
        _standard_headings(content),
        _contact_in_body(layout, content),
        _font_sizes(layout),
    ]


def keyword_hits(text: str, keywords: Sequence[Keyword]) -> dict[str, bool]:
    """Term → present in `text` (itself or one of its variants, whole words; case, accents,
    punctuation and simple plural ignored, like the coverage)."""
    return {
        keyword.term: any(
            contains_term(text, form, plural=True) for form in (keyword.term, *keyword.variants)
        )
        for keyword in keywords
    }

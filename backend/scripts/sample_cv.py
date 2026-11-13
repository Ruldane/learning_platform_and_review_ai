"""CV fictifs écrits à la main (aucune dépendance, comme `sample_pdf`) : identité « Camille
Exemple », domaines `example.org` seulement, entreprises et école inventées. Jamais un vrai CV.

Le PDF a un bandeau de couleur (rectangle rempli) avec le nom (22 pt gras) et le titre (13 pt),
puis deux colonnes : à gauche, sur fond gris, le contact, les compétences et les langues ; à
droite, le profil, les expériences (puces) et la formation. Le flux du contenu écrit la colonne de
gauche entière avant celle de droite (ordre lu par un parseur). Utilisé par les tests (extraction
de mise en page, gabarit, profil maître, revue) et par les contrôles réels."""

from dataclasses import dataclass
from typing import Literal

Rgb = tuple[float, float, float]

PAGE_SIZES: dict[str, tuple[int, int]] = {"A4": (595, 842), "Letter": (612, 792)}
_HEADER = b"%PDF-1.4\n"
_WHITE: Rgb = (1.0, 1.0, 1.0)
_INK: Rgb = (0.13, 0.13, 0.13)
_MUTED: Rgb = (0.4, 0.4, 0.4)
_PANEL: Rgb = (0.93, 0.93, 0.93)
_BAND_HEIGHT = 110
_PANEL_WIDTH = 190
# Polices standard (métriques connues de tous les lecteurs) et leur graisse grasse.
_STANDARD_BOLD = {
    "Helvetica": "Helvetica-Bold",
    "Times-Roman": "Times-Bold",
    "Courier": "Courier-Bold",
}
# Autre police (non embarquée) : chasse uniforme déclarée, pour que tout lecteur place les lettres.
_UNIFORM_WIDTH = 556

# Ce que contient le CV fictif : chaque valeur figure telle quelle dans le PDF.
CV_FACTS: dict[str, str] = {
    "name": "Camille Exemple",
    "title": "Développeuse Python et IA",
    "email": "camille.exemple@example.org",
    "phone": "+33 6 00 00 00 00",
    "city": "Lyon",
    "role_1": "Développeuse IA",
    "company_1": "Atelier Fictif",
    "period_1": "2023 – 2026",
    "role_2": "Développeuse Python",
    "company_2": "Données Exemple",
    "period_2": "2020 – 2023",
    "metric_1": "30 %",
    "metric_2": "12 000",
    "tools": "Python, FastAPI, LangGraph, Docker, SQL",
    "degree": "Master Informatique",
    "school": "Université Exemple",
    "language": "Anglais C1",
}
_SKILLS = ("Python", "FastAPI", "LangGraph", "Docker", "SQL")


@dataclass(frozen=True)
class SampleCv:
    name: str = CV_FACTS["name"]
    columns: Literal[1, 2] = 2
    pages: int = 1
    page: Literal["A4", "Letter"] = "A4"
    font: str = "Helvetica"
    accent: Rgb = (0.13, 0.33, 0.6)
    hidden_text: str | None = None
    scanned: bool = False


# Une ligne de texte : (x, y de la ligne de base, gras, taille, couleur, texte).
_Text = tuple[float, float, bool, float, Rgb, str]
# Un rectangle rempli : (x, y, largeur, hauteur, couleur).
_Rect = tuple[float, float, float, float, Rgb]


def _num(value: float) -> bytes:
    return (f"{value:.3f}".rstrip("0").rstrip(".") or "0").encode()


def _escape(text: str) -> bytes:
    """Chaîne PDF littérale : `\\`, `(` et `)` échappés ; hors cp1252 → `?`."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return escaped.encode("cp1252", errors="replace")


def _color(rgb: Rgb) -> bytes:
    return b" ".join(_num(part) for part in rgb) + b" rg"


def _rect_op(rect: _Rect) -> bytes:
    x, y, width, height, rgb = rect
    return _color(rgb) + b" %b %b %b %b re f" % (_num(x), _num(y), _num(width), _num(height))


def _text_op(text: _Text) -> bytes:
    x, y, bold, size, rgb, value = text
    font = b"/F2" if bold else b"/F1"
    return (
        b"BT %b %b Tf " % (font, _num(size))
        + _color(rgb)
        + b" %b %b Td (%b) Tj ET" % (_num(x), _num(y), _escape(value))
    )


def _section(x: float, y: float, title: str, lines: list[str], cv: SampleCv) -> list[_Text]:
    """Titre de section (11 pt gras, couleur d'accent) puis ses lignes (9 pt), de haut en bas."""
    out: list[_Text] = [(x, y, True, 11, cv.accent, title)]
    for index, line in enumerate(lines, start=1):
        out.append((x, y - 4 - 13 * index, False, 9, _INK, line))
    return out


def _experiences(x: float, top: float, cv: SampleCv) -> list[_Text]:
    facts = CV_FACTS
    rows: list[tuple[bool, float, Rgb, str]] = [
        (True, 12, cv.accent, "Expériences"),
        (True, 10.5, _INK, f"{facts['role_1']} — {facts['company_1']}"),
        (False, 9, _MUTED, f"{facts['period_1']}, {facts['city']}"),
        (False, 10, _INK, "• Conçu un assistant interne avec LangGraph pour le support"),
        (False, 10, _INK, f"• Réduit de {facts['metric_1']} le temps de traitement des demandes"),
        (False, 10, _INK, f"• Outils : {facts['tools']}"),
        (True, 10.5, _INK, f"{facts['role_2']} — {facts['company_2']}"),
        (False, 9, _MUTED, f"{facts['period_2']}, {facts['city']}"),
        (False, 10, _INK, f"• Automatisé le contrôle de {facts['metric_2']} factures par mois"),
        (False, 10, _INK, "• Écrit les tests et la documentation des services de données"),
        (True, 12, cv.accent, "Formation"),
        (True, 10.5, _INK, f"{facts['degree']} — {facts['school']}"),
        (False, 9, _MUTED, "2020"),
    ]
    return [
        (x, top - 17 * index, bold, size, rgb, text)
        for index, (bold, size, rgb, text) in enumerate(rows)
    ]


def _profile(x: float, top: float, cv: SampleCv) -> list[_Text]:
    return [
        (x, top, True, 12, cv.accent, "Profil"),
        (x, top - 18, False, 10, _INK, f"{CV_FACTS['title']}, cinq ans d'expérience en données"),
        (
            x,
            top - 31,
            False,
            10,
            _INK,
            "et en agents conversationnels. Aime livrer des outils utiles.",
        ),
    ]


def _first_page(cv: SampleCv, width: float, height: float) -> tuple[list[_Rect], list[_Text]]:
    facts = CV_FACTS
    band_y = height - _BAND_HEIGHT
    rects: list[_Rect] = [(0, band_y, width, _BAND_HEIGHT, cv.accent)]
    texts: list[_Text] = [
        (36, height - 58, True, 22, _WHITE, cv.name),
        (36, height - 82, False, 13, _WHITE, facts["title"]),
    ]
    contact = [facts["email"], facts["phone"], f"{facts['city']}, France"]
    languages = ["Français (langue maternelle)", facts["language"]]
    if cv.columns == 2:
        rects.append((0, 0, _PANEL_WIDTH, band_y, _PANEL))
        texts += _section(24, band_y - 30, "Contact", contact, cv)
        texts += _section(24, band_y - 110, "Compétences", list(_SKILLS), cv)
        texts += _section(24, band_y - 220, "Langues", languages, cv)
        right = _PANEL_WIDTH + 22
        texts += _profile(right, band_y - 30, cv)
        texts += _experiences(right, band_y - 90, cv)
    else:
        texts.append((40, band_y - 24, False, 9, _INK, " · ".join(contact)))
        texts += _profile(40, band_y - 56, cv)
        texts += _experiences(40, band_y - 116, cv)
        texts += _section(40, band_y - 360, "Compétences", [", ".join(_SKILLS)], cv)
        texts += _section(40, band_y - 410, "Langues", [", ".join(languages)], cv)
    if cv.hidden_text is not None:
        # Texte piégé : blanc, 1 pt, sur fond blanc (invisible à l'œil, lu par un parseur).
        texts.append((width - 200, 40, False, 1, _WHITE, cv.hidden_text))
    return rects, texts


def _next_page(cv: SampleCv, number: int, height: float) -> tuple[list[_Rect], list[_Text]]:
    texts: list[_Text] = [(40, height - 50, False, 9, _MUTED, f"{cv.name} — page {number}")]
    projects = [
        f"• Projet fictif n° {number}.{index} : outil interne de suivi" for index in (1, 2, 3)
    ]
    texts += _section(40, height - 90, "Projets", projects, cv)
    return [], texts


def _scanned(rects: list[_Rect], texts: list[_Text]) -> list[_Rect]:
    """Page « scannée » : le dessin seul, chaque ligne de texte devenue une barre grise."""
    bars: list[_Rect] = [
        (x, y, max(4 * size * len(value) / 8, 4), size * 0.7, (0.55, 0.55, 0.55))
        for x, y, _bold, size, _rgb, value in texts
    ]
    return rects + bars


def _page_content(cv: SampleCv, number: int) -> bytes:
    width, height = PAGE_SIZES[cv.page]
    if number == 1:
        rects, texts = _first_page(cv, width, height)
    else:
        rects, texts = _next_page(cv, number, height)
    if cv.scanned:
        return b"\n".join(_rect_op(rect) for rect in _scanned(rects, texts))
    return b"\n".join([*(_rect_op(rect) for rect in rects), *(_text_op(text) for text in texts)])


def _pdf_name(font: str) -> bytes:
    return font.encode("ascii", errors="replace").replace(b" ", b"")


def _standard(font: str) -> bool:
    return font.split("-")[0] in {"Helvetica", "Times", "Courier"}


def _font(base_font: str, descriptor: int) -> bytes:
    """Police non embarquée ; une police hors des 14 standard a, comme dans un vrai PDF, un
    descripteur (son nom) et des chasses déclarées."""
    body = b"<< /Type /Font /Subtype /Type1 /BaseFont /%b /Encoding /WinAnsiEncoding" % _pdf_name(
        base_font
    )
    if not _standard(base_font):
        widths = b" ".join([b"%d" % _UNIFORM_WIDTH] * 224)
        body += b" /FirstChar 32 /LastChar 255 /Widths [%b]" % widths
        body += b" /FontDescriptor %d 0 R" % descriptor
    return body + b" >>"


def _descriptor(base_font: str) -> bytes:
    return (
        b"<< /Type /FontDescriptor /FontName /%b /Flags 32 /FontBBox [-200 -250 1200 950]"
        b" /ItalicAngle 0 /Ascent 950 /Descent -250 /CapHeight 700 /StemV 80 >>"
        % _pdf_name(base_font)
    )


def assemble_pdf(objects: list[bytes], *, trailer_extra: bytes = b"") -> bytes:
    """Fichier PDF à partir des corps d'objets (numérotés à partir de 1, le 1 étant le catalogue) :
    table `xref` calculée."""
    out = bytearray(_HEADER)
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R%b >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        trailer_extra,
        xref,
    )
    return bytes(out)


def _objects(cv: SampleCv) -> list[bytes]:
    width, height = PAGE_SIZES[cv.page]
    bold = _STANDARD_BOLD.get(cv.font, f"{cv.font}-Bold")
    first_page = 7
    kids = b" ".join(b"%d 0 R" % (first_page + 2 * index) for index in range(cv.pages))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%b] /Count %d >>" % (kids, cv.pages),
        _font(cv.font, 5),
        _font(bold, 6),
        _descriptor(cv.font),
        _descriptor(bold),
    ]
    for index in range(cv.pages):
        stream = _page_content(cv, index + 1)
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] " % (width, height)
            + b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>"
            % (first_page + 2 * index + 1)
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    return objects


def make_cv_pdf(cv: SampleCv = SampleCv()) -> bytes:  # noqa: B008 (valeur figée)
    return assemble_pdf(_objects(cv))


def make_protected_pdf() -> bytes:
    """Le CV fictif déclaré chiffré (gestionnaire standard, RC4 40 bits) avec des empreintes de
    mot de passe qui ne correspondent à aucun mot de passe vide : il faut un mot de passe pour
    l'ouvrir."""
    objects = _objects(SampleCv())
    objects.append(
        b"<< /Filter /Standard /V 1 /R 2 /P -44 /O <%b> /U <%b> >>" % (b"6f" * 32, b"75" * 32)
    )
    trailer = b" /Encrypt %d 0 R /ID [<%b> <%b>]" % (len(objects), b"ab" * 16, b"ab" * 16)
    return assemble_pdf(objects, trailer_extra=trailer)


if __name__ == "__main__":
    import sys

    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sys.stdout.buffer.write(make_cv_pdf(SampleCv(pages=pages)))

"""HTML et CSS d'un CV, écrits par le code à partir du spec du Maquettiste (D118 n° 3, D120) : le
modèle ne produit jamais de HTML ni de CSS. Gabarit unique `cv/cv.html.j2` (échappement
automatique, variable inconnue = erreur), aucun script, aucune image, CSP en `<meta>`.

Aucune valeur du spec n'entre dans le CSS sans passer par son type validé : nombres finis et
bornés, couleurs `#rrggbb`, familles du catalogue des polices libres, styles d'une liste fermée.
Une valeur hors type lève `ValueError` (le spec doit avoir passé `template_problems`)."""

import math
import re
from collections.abc import Sequence
from urllib.parse import urlsplit

from app.agents.tools.cv_schema import CvContent, CvSection
from app.agents.tools.template_schema import ColumnBlock, TemplateSpec
from app.features.cv.service.targeted_content import TargetedCvContent
from app.providers.fonts.base import FontFile
from app.providers.fonts.catalog import (
    DEFAULT_SANS,
    DEFAULT_SERIF,
    FREE_FAMILIES,
    SERIF_FAMILIES,
)
from app.providers.pdf.base import HtmlDocument, PageSetup
from app.templates import render_template
from app.templates.assets import template_file

CV_CSP = (
    "default-src 'none'; style-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'"
)
_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_FONT_ASSET = re.compile(r"[a-z0-9][a-z0-9-]{0,56}\.(ttf|woff2)")
_FORMATS = {"ttf": "truetype", "woff2": "woff2"}
_FAMILIES = {family.casefold(): family for family in FREE_FAMILIES}
_TITLES = {"plain", "underline", "left_bar", "band"}
_DATES = {"right", "below", "left"}
_BULLETS = {"dot", "dash", "none"}
_POINTS_PER_INCH = 72
_MM_PER_INCH = 25.4
_DARK_LUMA = 140  # sous ce seuil, texte blanc sur le fond


def _number(value: float, low: float, high: float) -> str:
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("valeur numérique hors bornes")
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _hex(value: str) -> str:
    if not _HEX.fullmatch(value):
        raise ValueError("couleur hors du format #rrggbb")
    return value.lower()


def _family(name: str) -> str:
    family = _FAMILIES.get(name.casefold())
    if family is None:
        raise ValueError("police hors du catalogue des polices libres")
    return family


def _stack(name: str) -> str:
    family = _family(name)
    if family in SERIF_FAMILIES:
        return f"'{family}', '{DEFAULT_SERIF}', serif"
    return f"'{family}', '{DEFAULT_SANS}', sans-serif"


def _dark(color: str) -> bool:
    red, green, blue = (int(color[index : index + 2], 16) for index in (1, 3, 5))
    return 0.299 * red + 0.587 * green + 0.114 * blue < _DARK_LUMA


def _on(color: str, fallback: str) -> str:
    """Couleur lisible posée sur `color` : blanc sur un fond sombre, `fallback` sinon."""
    return "#ffffff" if _dark(color) else fallback


def _font_face(font: FontFile) -> str:
    if not _FONT_ASSET.fullmatch(font.asset_name) or font.style not in ("normal", "italic"):
        raise ValueError("fichier de police refusé")
    if font.weight not in range(100, 1000, 100):
        raise ValueError("graisse de police refusée")
    kind = _FORMATS[font.asset_name.rsplit(".", 1)[1]]
    return (
        f"@font-face {{ font-family: '{_family(font.family)}'; "
        f"src: url('{font.asset_name}') format('{kind}'); "
        f"font-weight: {font.weight}; font-style: {font.style}; }}"
    )


def _variables(spec: TemplateSpec) -> list[str]:
    page, fonts = spec.page, spec.fonts
    top, right, bottom, left = (_number(margin, 0, 40) for margin in page.margins_mm)
    text, accent = _hex(spec.text), _hex(spec.accent)
    band = _hex(spec.header_band) if spec.header_band is not None else None
    return [
        f"--page-w: {_number(page.width_pt, 200, 1000)}pt;",
        f"--page-h: {_number(page.height_pt, 200, 1400)}pt;",
        f"--m-top: {top}mm; --m-right: {right}mm; --m-bottom: {bottom}mm; --m-left: {left}mm;",
        f"--text: {text}; --accent: {accent}; --muted: {_hex(spec.muted)};",
        f"--accent-text: {_on(accent, text)};",
        f"--band: {band or 'transparent'}; --band-text: {_on(band, text) if band else text};",
        f"--body-font: {_stack(fonts.body)}; --heading-font: {_stack(fonts.heading)};",
        f"--body-pt: {_number(fonts.body_pt, 7, 14)}pt;",
        f"--heading-pt: {_number(max(fonts.heading_pt, fonts.body_pt), 7, 28)}pt;",
        f"--name-pt: {_number(fonts.name_pt, 12, 40)}pt;",
        f"--line-height: {_number(fonts.line_height, 1, 1.8)};",
        f"--gap: {_number(spec.gap_mm, 0, 20)}mm;",
    ]


def _columns_css(spec: TemplateSpec) -> list[str]:
    widths = " ".join(f"{_number(column.width_pct, 15, 100)}%" for column in spec.columns)
    rules = [f":root {{ --grid: {widths}; }}"]
    for rank, column in enumerate(spec.columns, start=1):
        background = _hex(column.background) if column.background else "transparent"
        dark = background != "transparent" and _dark(background)
        if column.text_color:
            color = title = _hex(column.text_color)
        elif dark:  # fond sombre sans couleur de texte : texte blanc, jamais illisible
            color = title = "#ffffff"
        else:
            color, title = "var(--text)", "var(--accent)"
        muted = "--muted: #d9d9d9; " if dark and not column.text_color else ""
        rules.append(f".col-{rank} {{ background: {background}; color: {color}; {muted}}}")
        rules.append(f"body:not(.titles-band) .col-{rank} h2 {{ color: {title}; }}")
    return rules


def cv_css(spec: TemplateSpec, fonts: Sequence[FontFile]) -> str:
    """Feuille du design : `@page` à la taille du spec (marges nulles : la mise en page est dans
    le corps), `@font-face` de chaque police jointe (URL relative à son nom de ressource),
    variables (couleurs, polices, tailles, marges), grille à une ou deux colonnes."""
    width, height = _number(spec.page.width_pt, 200, 1000), _number(spec.page.height_pt, 200, 1400)
    lines = [f"@page {{ size: {width}pt {height}pt; margin: 0; }}"]
    lines += [_font_face(font) for font in fonts]
    lines += [":root {", *(f"  {variable}" for variable in _variables(spec)), "}"]
    lines += _columns_css(spec)
    return "\n".join(lines) + "\n"


def _blocks(
    block: ColumnBlock, by_key: dict[str, list[CvSection]]
) -> list[ColumnBlock | CvSection]:
    if block == "identity":
        return ["identity"]
    return list(by_key.get(block, []))


def _place(spec: TemplateSpec, content: CvContent) -> list[list[ColumnBlock | CvSection]]:
    """Blocs de chaque colonne dans l'ordre du spec ; une section du contenu absente du spec va à
    la fin de la colonne la plus large (rien n'est perdu) ; sans bloc « identity » dans le spec,
    l'identité ouvre la première colonne."""
    by_key: dict[str, list[CvSection]] = {}
    for section in content.sections:  # deux sections de même clé : rendues toutes les deux
        by_key.setdefault(section.key, []).append(section)
    placed = {block for column in spec.columns for block in column.sections}
    columns: list[list[ColumnBlock | CvSection]] = [
        [item for block in column.sections for item in _blocks(block, by_key)]
        for column in spec.columns
    ]
    widest = max(range(len(spec.columns)), key=lambda rank: spec.columns[rank].width_pct)
    columns[widest] += [section for section in content.sections if section.key not in placed]
    if "identity" not in placed:
        columns[0].insert(0, "identity")
    return columns


def _inches(points: float) -> str:
    return f"{points / _POINTS_PER_INCH:.4f}".rstrip("0").rstrip(".")


def _classes(spec: TemplateSpec, band: bool) -> str:
    if (
        spec.section_title not in _TITLES
        or spec.dates not in _DATES
        or spec.bullets not in _BULLETS
    ):
        raise ValueError("style hors liste")
    classes = [f"titles-{spec.section_title}", f"dates-{spec.dates}", f"bullets-{spec.bullets}"]
    if spec.uppercase_titles:
        classes.append("upper")
    if band:
        classes.append("has-band")
    return " ".join(classes)


def _web_href(url: str) -> str | None:
    """Un lien Web imprimé peut devenir cliquable. Les autres valeurs restent du texte."""
    url = url.strip()
    if not url or any(char.isspace() or ord(char) < 32 or char == "\\" for char in url):
        return None
    try:
        parsed = urlsplit(url)
        if not parsed.scheme and not url.startswith(("/", "#", "?")):
            url = f"https://{url}"
            parsed = urlsplit(url)
            if "." not in (parsed.hostname or ""):
                return None
        if parsed.scheme in ("https", "http") and parsed.hostname and parsed.username is None:
            return url
    except ValueError:
        return None
    return None


def _skill_columns(spec: TemplateSpec, rank: int) -> int:
    _, right, _, left = spec.page.margins_mm
    left = left if rank == 0 else spec.gap_mm
    right = right if rank == len(spec.columns) - 1 else spec.gap_mm
    available_pt = spec.page.width_pt * spec.columns[rank].width_pct / 100
    available_pt -= (left + right) * _POINTS_PER_INCH / _MM_PER_INCH
    # Laisse environ sept cadratins par compétence, gouttière de 0,6 em comprise.
    return max(1, min(3, int(available_pt / (7 * spec.fonts.body_pt))))


def cv_document(spec: TemplateSpec, content: CvContent, fonts: Sequence[FontFile]) -> HtmlDocument:
    """Le CV à rendre : `index.html` (ordre du DOM = colonne 1 puis colonne 2, intitulés en
    `<h2>`, coordonnées dans le corps), `base.css`, `cv.css` et les polices jointes ; page à la
    taille du spec, marges nulles, sans pied de page. Avec un bandeau (`header_band`) et
    l'identité en tête de sa colonne, l'identité passe dans un bandeau pleine largeur, avant les
    colonnes."""
    columns = _place(spec, content)
    band = spec.header_band is not None and any(column[:1] == ["identity"] for column in columns)
    if band:
        columns = [[block for block in column if block != "identity"] for column in columns]
    targeted = isinstance(content, TargetedCvContent)
    index = render_template(
        "cv/cv.html.j2",
        csp=CV_CSP,
        content=content,
        columns=columns,
        header_links=[(link, _web_href(link.url)) for link in content.header_links]
        if isinstance(content, TargetedCvContent)
        else [],
        skill_columns=[
            _skill_columns(spec, rank) if targeted else 1 for rank in range(len(columns))
        ],
        band=band,
        classes=_classes(spec, band),
    )
    assets = {
        "base.css": template_file("cv/base.css").encode(),
        "cv.css": cv_css(spec, fonts).encode(),
        **{font.asset_name: font.data for font in fonts},
    }
    page = PageSetup(_inches(spec.page.width_pt), _inches(spec.page.height_pt))
    return HtmlDocument(index_html=index, assets=assets, page=page)

"""Polices d'un gabarit de CV (D119, D126). Le texte prend la police la plus employée (en
caractères), les titres celle des plus grandes tailles hors du nom ; chacune est remplacée par sa
famille libre (`choose_font`). Les fichiers d'une famille sont téléchargés une fois, rangés dans le
stockage (catégorie `cv_fonts`, suffixe du fichier reçu) et réutilisés d'un gabarit à l'autre.
Une famille introuvable (`FontUnavailable`) cède la place à Liberation Sans (ou Serif) de l'image
de Gotenberg, sans fichier joint.

Un écart de police est toujours dit à January, **sans le nom lu dans le PDF** : seules les
familles du catalogue apparaissent. Journaux : identifiants et nombres seulement (17.2)."""

import logging
import re
from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

from app.agents.tools.template_schema import FontUse
from app.features.cv.repository import TemplateRepository
from app.features.cv.service.runtime import CvRuntime
from app.providers.fonts.base import DEFAULT_WEIGHTS, FontFile, FontUnavailable
from app.providers.fonts.catalog import (
    DEFAULT_SANS,
    DEFAULT_SERIF,
    SERIF_FAMILIES,
    SUBSTITUTES,
    FontChoice,
    choose_font,
    clean_name,
)
from app.providers.pdf.base import PdfLayout, TextBlock

logger = logging.getLogger(__name__)

Role = Literal["body", "heading"]
FONT_CATEGORY = "cv_fonts"
# Familles aux métriques compatibles avec la police propriétaire qu'elles remplacent.
CLOSE_FAMILIES = frozenset({DEFAULT_SANS, DEFAULT_SERIF, "Carlito", "Caladea"})
# Familles installées dans l'image de Gotenberg : rendues même sans fichier joint.
IMAGE_FAMILIES = (DEFAULT_SANS, DEFAULT_SERIF)
SCANNED_GAP = "Les polices d'un CV scanné ne se lisent pas : le modèle emploie Liberation Sans."
_LABELS: dict[tuple[Role, ...], str] = {
    ("body",): "du texte",
    ("heading",): "des titres",
    ("body", "heading"): "du texte et des titres",
}


@dataclass(frozen=True)
class FontRole:
    """Police d'un rôle telle que lue dans le PDF. `original` : nom nettoyé (donnée du CV, jamais
    journalisée ni rendue par l'API) ; `known` : la police a un substitut connu."""

    role: Role
    original: str
    family: str
    free: bool
    known: bool


@dataclass(frozen=True)
class StoredFont:
    family: str
    weight: int
    style: Literal["normal", "italic"]
    suffix: Literal[".woff2", ".ttf"]
    key: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StoredFont":
        return cls(**data)


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _role(role: Role, pdf_font: str) -> FontRole:
    choice = choose_font(pdf_font)
    known = not choice.free and any(_key(choice.original).startswith(p) for p in SUBSTITUTES)
    return FontRole(role, choice.original, choice.family, choice.free, known)


def _heading(visible: list[TextBlock], first_page: list[TextBlock], body_size: float) -> str | None:
    """Police du plus grand texte plus grand que le corps, hors du nom (le plus grand texte de la
    première page) ; à taille égale, la plus employée."""
    name_size = max((b.size for b in first_page), default=None)
    larger = [b for b in visible if round(b.size, 1) > body_size and b.size != name_size]
    if not larger:
        return None
    top = max(round(b.size, 1) for b in larger)
    chars: Counter[str] = Counter()
    for block in larger:
        if round(block.size, 1) == top:
            chars[clean_name(block.font)] += len(block.text)
    return chars.most_common(1)[0][0]


def font_roles(layout: PdfLayout) -> list[FontRole]:
    """Le texte et les titres ; aucune police pour un CV scanné (aucun texte visible)."""

    def shown(blocks: Sequence[TextBlock]) -> list[TextBlock]:
        return [b for b in blocks if not b.invisible and b.text.strip()]

    visible = [b for page in layout.pages for b in shown(page.blocks)]
    if not visible:
        return []
    chars: Counter[str] = Counter()
    sizes: Counter[float] = Counter()
    for block in visible:
        chars[clean_name(block.font)] += len(block.text.strip())
        sizes[round(block.size, 1)] += len(block.text.strip())
    body = chars.most_common(1)[0][0]
    heading = _heading(visible, shown(layout.pages[0].blocks), sizes.most_common(1)[0][0])
    return [_role("body", body), _role("heading", heading or body)]


def _fallback(family: str) -> str:
    return DEFAULT_SERIF if family in SERIF_FAMILIES else DEFAULT_SANS


def _sentence(label: str, role: FontRole, loaded: bool) -> str | None:
    if not loaded:
        return (
            f"La police {label} n'a pas pu être chargée : remplacée par {_fallback(role.family)}."
        )
    if role.free:
        return None
    if role.known:
        close = "très proche" if role.family in CLOSE_FAMILIES else "proche"
        return f"La police {label} n'est pas libre : remplacée par {role.family}, {close}."
    return f"La police {label} n'a pas d'équivalent connu : remplacée par {role.family}."


def font_gaps(roles: Sequence[FontRole], loaded: Collection[str]) -> list[str]:
    """Une phrase par écart ; deux rôles au même sort n'en font qu'une."""
    if not roles:
        return [SCANNED_GAP]
    groups: dict[tuple[str, bool, bool, bool], list[Role]] = {}
    for role in roles:
        ok = role.family in loaded or role.family in IMAGE_FAMILIES
        groups.setdefault((role.family, role.free, role.known, ok), []).append(role.role)
    gaps: list[str] = []
    for (family, free, known, ok), names in groups.items():
        role = FontRole(names[0], "", family, free, known)
        if (sentence := _sentence(_LABELS[tuple(names)], role, ok)) is not None:
            gaps.append(sentence)
    return gaps


def font_uses(roles: Sequence[FontRole], loaded: Collection[str]) -> list[FontUse]:
    if not roles:
        return [FontUse(role=r, family=DEFAULT_SANS, substitute=True) for r in ("body", "heading")]
    uses: list[FontUse] = []
    for role in roles:
        ok = role.family in loaded or role.family in IMAGE_FAMILIES
        family = role.family if ok else _fallback(role.family)
        uses.append(FontUse(role=role.role, family=family, substitute=not (role.free and ok)))
    return uses


async def _reusable(rt: CvRuntime, user_id: str, family: str) -> list[StoredFont] | None:
    """Fichiers déjà rangés de `family` (toutes les graisses voulues), d'un autre gabarit."""
    async with rt.session_factory() as db:
        rows = await TemplateRepository(db, user_id).prepared_rows()
    for row in rows:
        files = [StoredFont.from_json(f) for f in (row.prepared or {}).get("font_files", [])]
        mine = [f for f in files if f.family == family and f.style == "normal"]
        if {f.weight for f in mine} >= set(DEFAULT_WEIGHTS):
            return [f for f in mine if f.weight in DEFAULT_WEIGHTS]
    return None


async def _family(rt: CvRuntime, user_id: str, family: str) -> list[StoredFont] | None:
    """Fichiers de `family` réutilisés ou téléchargés puis rangés ; `None` s'ils manquent."""
    if (found := await _reusable(rt, user_id, family)) is not None:
        return found
    try:
        files = await rt.fonts.fetch(family, DEFAULT_WEIGHTS)
    except FontUnavailable:
        return None
    stored: list[StoredFont] = []
    for file in files:
        key = await rt.storage.save(user_id, FONT_CATEGORY, file.data, file.suffix)
        stored.append(StoredFont(file.family, file.weight, file.style, file.suffix, key))
    return stored


async def resolve_roles(
    rt: CvRuntime, user_id: str, roles: Sequence[FontRole]
) -> tuple[list[StoredFont], list[FontUse], list[str]]:
    """Fichiers rangés, polices employées et écarts des rôles lus dans le PDF."""
    stored: list[StoredFont] = []
    loaded: set[str] = set()
    for family in dict.fromkeys(role.family for role in roles):
        files = await _family(rt, user_id, family)
        if files is not None:
            stored += files
            loaded.add(family)
    logger.info(
        "Polices du gabarit : utilisateur %s, %d famille(s), %d chargée(s), %d fichier(s)",
        user_id,
        len({role.family for role in roles}),
        len(loaded),
        len(stored),
    )
    return stored, font_uses(roles, loaded), font_gaps(roles, loaded)


async def load_files(
    rt: CvRuntime, user_id: str, stored: Sequence[StoredFont], families: Collection[str]
) -> list[FontFile]:
    """Les fichiers rangés des familles citées, relus du stockage."""
    files: list[FontFile] = []
    for font in stored:
        if font.family in families:
            data = await rt.storage.read(user_id, font.key)
            files.append(FontFile(font.family, font.weight, font.style, data, font.suffix))
    return files


def available_families(stored: Sequence[StoredFont]) -> list[str]:
    """Familles qu'un `TemplateSpec` peut citer : celles qui ont des fichiers, puis celles de
    l'image de Gotenberg."""
    return list(dict.fromkeys([*(font.family for font in stored), *IMAGE_FAMILIES]))


async def resolve_fonts(
    rt: CvRuntime, user_id: str, layout: PdfLayout
) -> tuple[list[FontFile], list[FontUse], list[str]]:
    """Fichiers des polices employées (joints au rendu), polices employées et écarts."""
    stored, uses, gaps = await resolve_roles(rt, user_id, font_roles(layout))
    return await load_files(rt, user_id, stored, {use.family for use in uses}), uses, gaps


def offered_choices(roles: Sequence[FontRole], available: Collection[str]) -> list[FontChoice]:
    """Polices libres retenues, ramenées à ce qui est réellement disponible : une famille sans
    fichier ni présence dans l'image cède la place à son repli (revue 6.10, M1)."""
    return [
        FontChoice(r.original, r.family, r.free)
        if r.family in available
        else FontChoice(r.original, _fallback(r.family), False)
        for r in roles
    ]


def offered_summary(summary: str, available: Collection[str]) -> str:
    """Blocs résumés dont la colonne « police » ne cite que des familles disponibles."""
    lines: list[str] = []
    for line in summary.splitlines():
        parts = line.split(" | ", 2)
        if len(parts) == 3 and parts[1] not in available:
            line = " | ".join((parts[0], _fallback(parts[1]), parts[2]))
        lines.append(line)
    return "\n".join(lines)


def roles_to_json(roles: Sequence[FontRole]) -> list[dict[str, Any]]:
    return [asdict(role) for role in roles]


def roles_from_json(data: Sequence[dict[str, Any]]) -> list[FontRole]:
    return [FontRole(**{**item, "role": cast(Role, item["role"])}) for item in data]

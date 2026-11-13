"""Score de ressemblance entre le CV d'origine et le rendu de son gabarit (SPEC 5.2 : « fidèle, pas
identique au pixel » ; D120). Trois parts sur une grille de `GRID_PT` points : l'encre (cellules
qui ont un pixel sombre), les boîtes de texte et les couleurs dominantes. L'encre et le texte se
comparent **avec une cellule de tolérance** : une cellule compte si l'autre côté a de l'encre (du
texte) dans son voisinage 3 × 3, pour qu'un décalage de quelques points (police substituée,
moteur de rendu) ne fasse pas chuter le score, alors qu'un interligne différent le fait. Les
écarts sont dits au Maquettiste en phrases françaises (`describe`).

Module pur partagé par le Maquettiste (6.9) et les gabarits (6.10) : il vit dans `agents/tools`
car le moteur n'importe aucune feature (contrat 6)."""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from app.agents.tools.template_grids import (
    GRID_PT,
    INK_LUMA,
    SHIFT_MAX_PT,
    SHIFT_MIN_PT,
    ZONES,
    Grid,
    ShiftCosts,
    Zone,
    accent_differs,
    color_match,
    dilate,
    ink_grid,
    page_shape,
    palette,
    text_grid,
    zone_views,
)
from app.providers.pdf.base import PageLayout

__all__ = [
    "GRID_PT",
    "INK_LUMA",
    "MAX_FIX_PASSES",
    "TARGET_SCORE",
    "W_COLOR",
    "W_INK",
    "W_TEXT",
    "Similarity",
    "Zone",
    "ZoneDiff",
    "ZoneMatch",
    "describe",
    "similarity",
]

TARGET_SCORE = 85
MAX_FIX_PASSES = 3
W_INK, W_TEXT, W_COLOR = 0.45, 0.35, 0.20
# Description : écarts de part d'encre de plus de 5 points seulement, 4 phrases au plus.
ZONE_THRESHOLD = 5
MAX_ZONE_SENTENCES = 4
TOLERANT_SHARE = 0.5  # part du recouvrement tolérant dans l'encre et le texte (D120)
_FULL = 0.99  # une composante à 99 % ou plus n'est pas « la plus faible »

_ZONE_WORDS: dict[Zone, str] = {
    "haut": "en haut",
    "milieu": "au milieu",
    "bas": "en bas",
    "gauche": "à gauche",
    "droite": "à droite",
}


@dataclass(frozen=True)
class ZoneDiff:
    """Part d'encre (0 à 1 : cellules encrées / cellules de la zone, toutes pages) d'une zone :
    tiers haut, milieu, bas ; moitiés gauche, droite."""

    zone: Zone
    original: float
    render: float


@dataclass(frozen=True)
class ZoneMatch:
    """Recouvrement (avec tolérance) de l'encre et du texte dans une zone, de 0 à 1."""

    zone: Zone
    ink: float
    text: float


@dataclass(frozen=True)
class Similarity:
    """`score` est plafonné à `TARGET_SCORE − 1` si le nombre de pages diffère ;
    `accent_differs` : la couleur d'accent du rendu n'est pas celle de l'original ; `shifts` :
    décalage vertical du rendu (points, positif vers le bas) par tiers haut, milieu, bas."""

    score: int
    ink: float
    text: float
    color: float
    pages_original: int
    pages_render: int
    zones: list[ZoneDiff]
    matches: list[ZoneMatch] = field(default_factory=list)
    accent_differs: bool = False
    shifts: dict[Zone, int] = field(default_factory=dict)


@dataclass
class _Overlap:
    """Comptes de l'encre (ou du texte) des deux côtés, au total et par zone : recouvrement
    tolérant (cellules de A près de B + cellules de B près de A) / (cellules de A + de B), et IoU
    stricte (A et B / A ou B)."""

    hit: Counter[Zone | None] = field(default_factory=Counter)
    total: Counter[Zone | None] = field(default_factory=Counter)
    inter: Counter[Zone | None] = field(default_factory=Counter)
    union: Counter[Zone | None] = field(default_factory=Counter)

    def add(self, first: Grid, second: Grid) -> None:
        hits = (first & dilate(second)).astype(np.int32) + (second & dilate(first)).astype(np.int32)
        grids = {
            "hit": hits,
            "total": first.astype(np.int32) + second.astype(np.int32),
            "inter": first & second,
            "union": first | second,
        }
        for name, grid in grids.items():
            counter: Counter[Zone | None] = getattr(self, name)
            counter[None] += int(grid.sum())
            for zone, view in zone_views(grid).items():
                counter[zone] += int(view.sum())

    def ratio(self, zone: Zone | None = None) -> float:
        """Moyenne du recouvrement tolérant et de l'IoU stricte (aucune cellule : 1)."""
        tolerant = self.hit[zone] / self.total[zone] if self.total[zone] else 1.0
        strict = self.inter[zone] / self.union[zone] if self.union[zone] else 1.0
        return TOLERANT_SHARE * tolerant + (1 - TOLERANT_SHARE) * strict


@dataclass
class _Tally:
    ink: _Overlap = field(default_factory=_Overlap)
    text: _Overlap = field(default_factory=_Overlap)
    cells: Counter[Zone] = field(default_factory=Counter)
    original: Counter[Zone] = field(default_factory=Counter)
    render: Counter[Zone] = field(default_factory=Counter)
    shift: ShiftCosts = field(default_factory=ShiftCosts)

    def add(self, page_o: PageLayout | None, page_r: PageLayout | None) -> None:
        shapes = [page_shape(page) for page in (page_o, page_r) if page is not None]
        shape = (max(s[0] for s in shapes), max(s[1] for s in shapes))
        if page_o is not None and page_r is not None:
            self.shift.add(page_o, page_r, shape[0] * GRID_PT)
        ink_o, ink_r, text_o, text_r = (
            grid(page, shape) if page is not None else np.zeros(shape, dtype=np.bool_)
            for grid, page in (
                (ink_grid, page_o),
                (ink_grid, page_r),
                (text_grid, page_o),
                (text_grid, page_r),
            )
        )
        self.ink.add(ink_o, ink_r)
        self.text.add(text_o, text_r)
        render_zones = zone_views(ink_r)
        for zone, cells in zone_views(ink_o).items():
            self.cells[zone] += cells.size
            self.original[zone] += int(cells.sum())
            self.render[zone] += int(render_zones[zone].sum())

    def zones(self) -> list[ZoneDiff]:
        return [
            ZoneDiff(
                zone=zone,
                original=self.original[zone] / self.cells[zone] if self.cells[zone] else 0.0,
                render=self.render[zone] / self.cells[zone] if self.cells[zone] else 0.0,
            )
            for zone in ZONES
        ]

    def matches(self) -> list[ZoneMatch]:
        return [ZoneMatch(zone, self.ink.ratio(zone), self.text.ratio(zone)) for zone in ZONES]


def similarity(original: Sequence[PageLayout], render: Sequence[PageLayout]) -> Similarity:
    """Pages appariées par rang (page absente : grille vide) ; encre et texte : recouvrement avec
    une cellule de tolérance sur toutes les pages (aucune cellule des deux côtés : 1) ; score
    arrondi au plus proche, plafonné sous la cible si le nombre de pages diffère. `ValueError` si
    une image n'est pas à la taille de sa page (72 dpi)."""
    tally = _Tally()
    for index in range(max(len(original), len(render))):
        page_o = original[index] if index < len(original) else None
        page_r = render[index] if index < len(render) else None
        tally.add(page_o, page_r)
    ink, text = tally.ink.ratio(), tally.text.ratio()
    palette_o, palette_r = palette(original), palette(render)
    color = color_match(palette_o, palette_r)
    score = min(
        100, max(0, math.floor(100 * (W_INK * ink + W_TEXT * text + W_COLOR * color) + 0.5))
    )
    if len(original) != len(render):
        score = min(score, TARGET_SCORE - 1)
    return Similarity(
        score=score,
        ink=ink,
        text=text,
        color=color,
        pages_original=len(original),
        pages_render=len(render),
        zones=tally.zones(),
        matches=tally.matches(),
        accent_differs=accent_differs(palette_o, palette_r),
        shifts=tally.shift.shifts(),
    )


def _weakest(sim: Similarity) -> str | None:
    """La composante la plus faible et la zone où elle l'est le plus (`None` si toutes sont à
    99 % ou plus)."""
    parts = {"ink": sim.ink, "text": sim.text, "color": sim.color}
    name = min(parts, key=lambda key: parts[key])
    value = parts[name]
    if value >= _FULL:
        return None
    percent = math.floor(100 * value)
    if name == "color":
        return (
            "Les couleurs du rendu s'écartent de celles de l'original "
            f"(ressemblance de {percent} %)."
        )
    subject = (
        "L'encre du rendu ne recouvre celle"
        if name == "ink"
        else "Les blocs de texte du rendu ne recouvrent ceux"
    )
    sentence = f"{subject} de l'original qu'à {percent} %"
    if sim.matches:
        zone = min(sim.matches, key=lambda match: getattr(match, name)).zone
        sentence += f", surtout {_ZONE_WORDS[zone]}"
    return sentence + "."


def _shift_sentence(shifts: dict[Zone, int]) -> str | None:
    """Sens et ampleur du plus grand décalage vertical (`SHIFT_MIN_PT` ou plus), et la piste de
    correction : dès le haut et à peu près égal partout → marge haute ; plus fort plus bas →
    interligne ou espaces entre blocs."""
    if not shifts:
        return None
    # À égalité (plafond atteint dans deux tiers), le tiers le plus bas : c'est là que l'écart naît.
    zone, points = max(reversed(list(shifts.items())), key=lambda item: abs(item[1]))
    if abs(points) < SHIFT_MIN_PT:
        return None
    amount = "d'au moins" if abs(points) >= SHIFT_MAX_PT else "d'environ"
    sentence = (
        f"Le contenu du rendu est décalé {'vers le bas' if points > 0 else 'vers le haut'} "
        f"{amount} {abs(points)} pt"
    )
    if zone == "haut" or abs(points - shifts.get("haut", 0)) < SHIFT_MIN_PT:
        return f"{sentence} dès le haut de la page : revoir la marge haute ou l'en-tête."
    return (
        f"{sentence}, surtout {_ZONE_WORDS[zone]} (l'écart grandit en descendant) : "
        "revoir l'interligne ou les espaces entre les blocs."
    )


def describe(sim: Similarity) -> str:
    """Phrases pour le Maquettiste. Sous `TARGET_SCORE`, toujours au moins une : la composante la
    plus faible et sa zone ; puis le décalage vertical s'il atteint `SHIFT_MIN_PT` (sens, zone,
    piste de correction) ; la couleur d'accent si elle diffère ; les zones dont la part d'encre
    diffère de plus de `ZONE_THRESHOLD` points (les plus grands écarts d'abord,
    `MAX_ZONE_SENTENCES` au plus) ; le nombre de pages s'il diffère. Chaîne vide si rien n'est à
    signaler."""
    sentences: list[str] = []
    weakest = _weakest(sim) if sim.score < TARGET_SCORE else None
    if weakest:
        sentences.append(weakest)
    shift = _shift_sentence(sim.shifts)
    if shift:
        sentences.append(shift)
    if sim.accent_differs:
        sentences.append("La couleur d'accent du rendu diffère de celle de l'original.")
    gaps = sorted(
        ((round(100 * (zone.render - zone.original)), zone.zone) for zone in sim.zones),
        key=lambda gap: -abs(gap[0]),
    )
    sentences += [
        f"Le rendu a {abs(points)} % d'encre en {'plus' if points > 0 else 'moins'} "
        f"{_ZONE_WORDS[zone]} que l'original."
        for points, zone in gaps
        if abs(points) > ZONE_THRESHOLD
    ][:MAX_ZONE_SENTENCES]
    if sim.pages_render != sim.pages_original:
        sentences.append(f"Pages : {sim.pages_render} au lieu de {sim.pages_original}.")
        sentences.append("Le rendu doit garder le nombre de pages de l'original.")
    return " ".join(sentences)

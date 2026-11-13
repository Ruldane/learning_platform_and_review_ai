"""Encre sous un bloc de texte, lue sur l'image rendue de la page (D119, revue 6.3, I1 et I2).

Un bloc n'est visible que si l'image montre de l'encre dans son cadre : au moins 2 % des pixels
s'écartent de la couleur dominante (le fond) de plus de 48 sur un canal. L'image rendue par PDFium
est la vérité : mode de rendu invisible (`3 Tr`, `7 Tr`), dessin posé sur le texte, opacité nulle,
rognage, calque masqué ou couleur proche du fond ne laissent aucune encre ; une couche OCR posée
sur un scan trouve l'encre des lettres numérisées et reste visible. Sans FastAPI ni base."""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

INK_MIN_DELTA = 48
INK_MIN_SHARE = 0.02

Rgb = tuple[int, int, int]
Pixels = NDArray[np.uint8]


@dataclass(frozen=True)
class Ink:
    """`share` : part des pixels encrés du cadre ; `color` : le pixel le plus éloigné du fond
    (cœur d'une lettre), `None` sans encre."""

    share: float
    color: Rgb | None

    @property
    def visible(self) -> bool:
        return self.share >= INK_MIN_SHARE


def pixels_of(image: object) -> Pixels:
    """Pixels RVB d'une image PIL (hauteur × largeur × 3)."""
    return np.asarray(image, dtype=np.uint8)


def measure_ink(pixels: Pixels, box: tuple[float, float, float, float], scale: float) -> Ink:
    """Encre dans `box` (points, repère de l'image), coupé aux bords de l'image."""
    x0, top, x1, bottom = box
    height, width = pixels.shape[0], pixels.shape[1]
    left, upper = max(math.floor(x0 * scale), 0), max(math.floor(top * scale), 0)
    right, lower = min(math.ceil(x1 * scale), width), min(math.ceil(bottom * scale), height)
    if right <= left or lower <= upper:
        return Ink(0.0, None)
    region = pixels[upper:lower, left:right].reshape(-1, 3).astype(np.int32)
    keys = (region[:, 0] << 16) | (region[:, 1] << 8) | region[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    background_key = int(values[int(np.argmax(counts))])
    background = np.array(
        [(background_key >> 16) & 0xFF, (background_key >> 8) & 0xFF, background_key & 0xFF]
    )
    delta = np.abs(region - background).max(axis=1)
    inked = delta > INK_MIN_DELTA
    if not inked.any():
        return Ink(0.0, None)
    core = region[int(np.argmax(delta))]
    return Ink(float(inked.mean()), (int(core[0]), int(core[1]), int(core[2])))

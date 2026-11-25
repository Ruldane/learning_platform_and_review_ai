"""Ink under a block of text, read from the rendered image of the page (D119, review 6.3, I1 and
I2).

A block is visible only if the image shows ink within its frame: at least 2% of the pixels differ
from the dominant colour (the background) by more than 48 on a channel. The image rendered by PDFium
is the truth: an invisible render mode (`3 Tr`, `7 Tr`), a drawing placed over the text, zero
opacity, clipping, a hidden layer, or a colour close to the background leave no ink; an OCR layer
placed on a scan finds the ink of the scanned letters and stays visible. No FastAPI, no database."""

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
    """`share`: share of inked pixels in the frame; `color`: the pixel furthest from the background
    (core of a letter), `None` without ink."""

    share: float
    color: Rgb | None

    @property
    def visible(self) -> bool:
        return self.share >= INK_MIN_SHARE


def pixels_of(image: object) -> Pixels:
    """RGB pixels of a PIL image (height × width × 3)."""
    return np.asarray(image, dtype=np.uint8)


def measure_ink(pixels: Pixels, box: tuple[float, float, float, float], scale: float) -> Ink:
    """Ink in `box` (points, image coordinates), cut at the edges of the image."""
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

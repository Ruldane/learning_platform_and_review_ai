"""Projection 2D de la carte de la mémoire : PCA par SVD (numpy). Fonction pure, déterministe :
le signe de chaque composante est fixé, donc deux appels sur le même nuage donnent la même carte."""

from collections.abc import Sequence

import numpy as np

# En deçà, un axe est considéré comme nul (nuage plat sur cet axe) : bruit d'arrondi de la SVD.
_FLAT = 1e-9


def project_2d(vectors: Sequence[Sequence[float]]) -> list[tuple[float, float]]:
    """Coordonnées de chaque vecteur sur les deux premières composantes principales.

    Centrage, SVD, deux premières composantes ; signe fixé (la plus grande charge en valeur
    absolue de chaque composante est positive) ; chaque axe divisé par son max absolu (0 si nul),
    d'où des coordonnées sur [-1, 1]. 0 vecteur : [] ; 1 vecteur : [(0.0, 0.0)]."""
    if not vectors:
        return []
    if len(vectors) == 1:
        return [(0.0, 0.0)]
    data = np.asarray(vectors, dtype=np.float64)
    centered = data - data.mean(axis=0)
    _, _, components = np.linalg.svd(centered, full_matrices=False)
    axes = np.zeros((len(vectors), 2))
    scale = max(float(np.abs(centered).max()), 1.0)
    for i, component in enumerate(components[:2]):
        if component[np.argmax(np.abs(component))] < 0:
            component = -component
        coords = centered @ component
        peak = float(np.abs(coords).max())
        if peak > _FLAT * scale:
            axes[:, i] = coords / peak
    return [(float(x), float(y)) for x, y in axes]

"""2D projection of the memory map: PCA by SVD (numpy). Pure, deterministic function:
the sign of each component is fixed, so two calls on the same cloud give the same map."""

from collections.abc import Sequence

import numpy as np

# Below this, an axis is considered null (flat cloud on that axis): SVD rounding noise.
_FLAT = 1e-9


def project_2d(vectors: Sequence[Sequence[float]]) -> list[tuple[float, float]]:
    """Coordinates of each vector on the first two principal components.

    Centering, SVD, first two components; fixed sign (the largest absolute loading of each
    component is positive); each axis divided by its absolute max (0 if null), hence
    coordinates in [-1, 1]. 0 vectors: []; 1 vector: [(0.0, 0.0)]."""
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

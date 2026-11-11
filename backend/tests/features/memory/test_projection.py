"""Projection 2D de la carte (PCA) : centrage, signe fixé, axes normalisés sur [-1, 1]."""

import pytest

from app.features.memory.service.projection import project_2d


def test_project_2d_line() -> None:
    pts = project_2d([[0, 0, 0], [1, 1, 0], [2, 2, 0]])
    assert pts == [
        pytest.approx((-1.0, 0.0)),
        pytest.approx((0.0, 0.0)),
        pytest.approx((1.0, 0.0)),
    ]


def test_project_2d_small_inputs() -> None:
    assert project_2d([]) == [] and project_2d([[3.0, 1.0]]) == [(0.0, 0.0)]
    assert project_2d([[0, 0], [2, 0]]) == [pytest.approx((-1.0, 0.0)), pytest.approx((1.0, 0.0))]


def test_project_2d_sign_is_fixed_and_axes_bounded() -> None:
    # Même nuage, ordre des points inversé : chaque point garde ses coordonnées (signe stable).
    cloud = [[1.0, 0.2, 0.0], [0.0, 1.0, 0.3], [0.5, 0.5, 1.0], [0.9, 0.1, 0.4]]
    forward = project_2d(cloud)
    backward = project_2d(cloud[::-1])[::-1]
    assert forward == [pytest.approx(p) for p in backward]
    for x, y in forward:
        assert -1.0 <= x <= 1.0 and -1.0 <= y <= 1.0
    assert max(abs(x) for x, _ in forward) == pytest.approx(1.0)
    assert max(abs(y) for _, y in forward) == pytest.approx(1.0)


def test_project_2d_identical_vectors_collapse_to_origin() -> None:
    assert project_2d([[0.3, 0.4], [0.3, 0.4], [0.3, 0.4]]) == [(0.0, 0.0)] * 3


def test_project_2d_one_dimension() -> None:
    assert project_2d([[1.0], [3.0]]) == [pytest.approx((-1.0, 0.0)), pytest.approx((1.0, 0.0))]

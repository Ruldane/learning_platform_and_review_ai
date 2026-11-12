import pytest

from app.core.skills import normalize_skill_name


@pytest.mark.parametrize(
    ("raw", "norm"),
    [
        ("  Réseaux de Neurones ", "reseaux de neurones"),
        ("PyTorch.", "pytorch"),
        ("Machine   Learning", "machine learning"),
        ("« Éléments finis »,", "elements finis"),
        ("C++", "c++"),
        ("Straße", "strasse"),
        ("", ""),
    ],
)
def test_normalize_skill_name(raw: str, norm: str) -> None:
    assert normalize_skill_name(raw) == norm


def test_normalize_is_idempotent() -> None:
    once = normalize_skill_name("  Déployer (Docker) ")
    assert normalize_skill_name(once) == once

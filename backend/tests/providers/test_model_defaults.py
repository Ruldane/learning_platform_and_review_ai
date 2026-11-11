import pytest

from app.providers.llm import model_defaults as md
from app.providers.llm.base import TIERS, ModelChoice


def test_defaults_are_anthropic_haiku_for_every_tier() -> None:
    haiku = ModelChoice(provider="anthropic", model="claude-haiku-5-5")
    assert set(md.DEFAULT_TIERS) == set(TIERS)
    assert all(c == haiku for c in md.DEFAULT_TIERS.values())
    assert md.ANTHROPIC_FAST == "claude-haiku-5-5" and md.ANTHROPIC_STRONG == "claude-sonnet-5-5"


def test_presets_cover_all_tiers() -> None:
    assert set(md.PRESETS) == {"all_haiku", "haiku_sonnet_strong", "all_glm", "all_openai"}
    for preset in md.PRESETS.values():
        assert set(preset) == set(TIERS)
    assert md.PRESETS["haiku_sonnet_strong"]["fort"].model == md.ANTHROPIC_STRONG
    assert md.PRESETS["haiku_sonnet_strong"]["rapide"].model == md.ANTHROPIC_FAST


def test_every_preset_has_a_vision_capable_vision_tier() -> None:
    for preset in md.PRESETS.values():
        assert md.supports_vision(preset["vision"])


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("anthropic", "claude-haiku-5-5", True),
        ("anthropic", "claude-sonnet-5-5", True),
        ("glm", md.GLM_VISION, True),
        ("glm", "glm-5.3-flash", True),
        ("glm", "glm-4.7-flash", False),
        ("glm", "glm-5.3", False),
        ("openai", md.OPENAI_VISION, True),
        ("openai", md.OPENAI_FAST, False),
        ("inconnu", "x", False),
    ],
)
def test_supports_vision(provider: str, model: str, expected: bool) -> None:
    assert md.supports_vision(ModelChoice(provider=provider, model=model)) is expected


def test_all_glm_preset_is_glm_5_3_flash_on_every_tier() -> None:
    flash = ModelChoice(provider="glm", model="glm-5.3-flash")
    assert md.PRESETS["all_glm"] == {tier: flash for tier in TIERS}
    assert md.GLM_FAST == md.GLM_STRONG == md.GLM_VISION == "glm-5.3-flash"

"""Default model identifiers, grouped here and nowhere else (spec 11.2).

Sources and survey dates: see DECISIONS.md (D25). To be rechecked at each change to the
providers' catalogues.
"""

from typing import Literal

from app.providers.llm.base import ModelChoice, Tier

ANTHROPIC_FAST = "claude-haiku-5-5"
ANTHROPIC_STRONG = "claude-sonnet-5-5"

OPENAI_FAST = "gpt-6-luna"
OPENAI_STRONG = "gpt-6.1-sol"
OPENAI_VISION = "gpt-6.1-terra"

# « Tout GLM »: glm-5.3-flash everywhere, the model January has credited and that sees the
# images; glm-5.3 and glm-4.7-flash are not reliable for January (D44).
GLM_FAST = "glm-5.3-flash"
GLM_STRONG = "glm-5.3-flash"
GLM_VISION = "glm-5.3-flash"

PresetName = Literal["all_haiku", "haiku_sonnet_strong", "all_glm", "all_openai"]


def _tiers(provider: str, fast: str, strong: str, vision: str) -> dict[Tier, ModelChoice]:
    return {
        "fast": ModelChoice(provider=provider, model=fast),
        "standard": ModelChoice(provider=provider, model=fast),
        "strong": ModelChoice(provider=provider, model=strong),
        "vision": ModelChoice(provider=provider, model=vision),
    }


DEFAULT_TIERS: dict[Tier, ModelChoice] = _tiers(
    "anthropic", ANTHROPIC_FAST, ANTHROPIC_FAST, ANTHROPIC_FAST
)

PRESETS: dict[PresetName, dict[Tier, ModelChoice]] = {
    "all_haiku": _tiers("anthropic", ANTHROPIC_FAST, ANTHROPIC_FAST, ANTHROPIC_FAST),
    "haiku_sonnet_strong": _tiers("anthropic", ANTHROPIC_FAST, ANTHROPIC_STRONG, ANTHROPIC_FAST),
    "all_glm": _tiers("glm", GLM_FAST, GLM_STRONG, GLM_VISION),
    "all_openai": _tiers("openai", OPENAI_FAST, OPENAI_STRONG, OPENAI_VISION),
}

# Explicit lists taken from the providers' documentation (survey of 2026-11-11).
_OPENAI_VISION_MODELS = frozenset({"gpt-6-astra", OPENAI_STRONG, OPENAI_VISION})
_GLM_VISION_MODELS = frozenset(
    {GLM_VISION, "glm-5.3-flashx", "glm-4.6v", "glm-4.6v-flash", "glm-4.6v-flashx", "glm-4.5v"}
)


def supports_vision(choice: ModelChoice) -> bool:
    """Does the model accept image input? Unknown = no (we turn it off instead)."""
    if choice.provider == "anthropic":
        return choice.model.startswith("claude-")
    if choice.provider == "openai":
        return choice.model in _OPENAI_VISION_MODELS
    if choice.provider == "glm":
        return choice.model in _GLM_VISION_MODELS
    return False

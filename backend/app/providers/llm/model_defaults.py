"""Identifiants de modèles par défaut, regroupés ici et nulle part ailleurs (spec 11.2).

Sources et dates de relevé : voir DECISIONS.md (D25). À revérifier à chaque évolution des
catalogues des fournisseurs.
"""

from typing import Literal

from app.providers.llm.base import ModelChoice, Tier

ANTHROPIC_FAST = "claude-haiku-5-5"
ANTHROPIC_STRONG = "claude-sonnet-5-5"

OPENAI_FAST = "gpt-6-luna"
OPENAI_STRONG = "gpt-6.1-sol"
OPENAI_VISION = "gpt-6.1-terra"

GLM_FAST = "glm-4.7-flash"
GLM_STRONG = "glm-5.3"
GLM_VISION = "glm-5.3-flash"

PresetName = Literal["all_haiku", "haiku_sonnet_strong", "all_glm", "all_openai"]


def _tiers(provider: str, fast: str, strong: str, vision: str) -> dict[Tier, ModelChoice]:
    return {
        "rapide": ModelChoice(provider=provider, model=fast),
        "standard": ModelChoice(provider=provider, model=fast),
        "fort": ModelChoice(provider=provider, model=strong),
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

# Listes explicites issues de la documentation des fournisseurs (relevé du 2026-11-11).
_OPENAI_VISION_MODELS = frozenset({"gpt-6-astra", OPENAI_STRONG, OPENAI_VISION})
_GLM_VISION_MODELS = frozenset(
    {GLM_VISION, "glm-5.3-flashx", "glm-4.6v", "glm-4.6v-flash", "glm-4.6v-flashx", "glm-4.5v"}
)


def supports_vision(choice: ModelChoice) -> bool:
    """Le modèle accepte-t-il des images en entrée ? Inconnu = non (on désactive plutôt)."""
    if choice.provider == "anthropic":
        return choice.model.startswith("claude-")
    if choice.provider == "openai":
        return choice.model in _OPENAI_VISION_MODELS
    if choice.provider == "glm":
        return choice.model in _GLM_VISION_MODELS
    return False

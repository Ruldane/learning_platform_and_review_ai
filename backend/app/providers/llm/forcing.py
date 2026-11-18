"""Fournisseur forcé pour tout un parcours : le choix de la personne est gardé s'il est déjà chez
ce fournisseur, sinon le modèle de son préréglage pour le niveau."""

from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.model_defaults import PRESETS, PresetName

_PRESET_OF: dict[str, PresetName] = {
    "anthropic": "haiku_sonnet_strong",
    "glm": "all_glm",
    "openai": "all_openai",
}


def forced_choice(choice: ModelChoice, provider: str, tier: Tier) -> ModelChoice:
    if choice.provider == provider or provider not in _PRESET_OF:
        return choice
    return PRESETS[_PRESET_OF[provider]][tier]

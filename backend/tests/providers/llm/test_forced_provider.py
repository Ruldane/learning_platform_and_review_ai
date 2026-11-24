"""Un parcours lancé avec « API GLM », « API Claude » ou « API OpenAI » force ce fournisseur sur
tous les niveaux : le choix de la personne est gardé s'il est déjà chez lui, sinon le modèle du
préréglage du fournisseur (`haiku_sonnet_strong`, `all_glm`, `all_openai`)."""

from collections.abc import Callable

from app.core.played import PLAY_CONTEXT, PlayContext
from app.providers.llm.base import ModelChoice
from app.providers.llm.factory import LlmFactory
from app.providers.llm.forcing import forced_choice
from app.providers.llm.model_defaults import PRESETS

FactoryWith = Callable[..., LlmFactory]


def test_same_provider_keeps_the_chosen_model() -> None:
    mine = ModelChoice(provider="glm", model="glm-4.6v")
    assert forced_choice(mine, "glm", "vision") == mine


def test_other_provider_takes_the_preset_model_of_the_tier() -> None:
    mine = ModelChoice(provider="anthropic", model="claude-haiku-5-5")
    assert forced_choice(mine, "glm", "strong") == PRESETS["all_glm"]["strong"]
    assert forced_choice(mine, "openai", "fast") == PRESETS["all_openai"]["fast"]
    other = ModelChoice(provider="glm", model="glm-5.3-flash")
    assert forced_choice(other, "anthropic", "strong") == PRESETS["haiku_sonnet_strong"]["strong"]


async def test_factory_follows_the_provider_of_the_run(factory_with: FactoryWith) -> None:
    f = factory_with(tiers={"strong": ("anthropic", "claude-sonnet-5-5")}, keys={"glm": "k"})
    flag = PLAY_CONTEXT.set(PlayContext("u1", None, provider="glm"))
    try:
        assert await f.resolve("u1", "strong") == PRESETS["all_glm"]["strong"]
        other_user = await f.resolve("u2", "strong")
    finally:
        PLAY_CONTEXT.reset(flag)
    assert other_user.provider == "anthropic"  # le contexte d'un compte ne vaut pas pour un autre
    assert (await f.resolve("u1", "strong")).provider == "anthropic"

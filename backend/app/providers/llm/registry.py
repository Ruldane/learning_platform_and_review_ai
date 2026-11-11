"""Registre des fournisseurs LLM réels. Le faux fournisseur n'y figure pas (tests seulement)."""

from pathlib import Path

from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.glm import GlmProvider
from app.providers.llm.openai import OpenAIProvider

# Prix en USD par million de tokens, éditable à la main (les tarifs évoluent), voir D26.
PRICES_PATH = Path(__file__).with_name("model_prices.json")

LLM_PROVIDERS: dict[str, LlmProvider] = {
    "anthropic": AnthropicProvider(),
    "openai": OpenAIProvider(),
    "glm": GlmProvider(),
}

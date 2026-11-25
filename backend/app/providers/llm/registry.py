"""Registry of the real LLM providers. The fake provider is not listed here (tests only)."""

from pathlib import Path

from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.base import LlmProvider
from app.providers.llm.glm import GlmProvider
from app.providers.llm.openai import OpenAIProvider

# USD price per million tokens, editable by hand (prices change), see D26.
PRICES_PATH = Path(__file__).with_name("model_prices.json")

LLM_PROVIDERS: dict[str, LlmProvider] = {
    "anthropic": AnthropicProvider(),
    "openai": OpenAIProvider(),
    "glm": GlmProvider(),
}

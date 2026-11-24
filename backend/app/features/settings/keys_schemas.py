from datetime import datetime
from typing import Literal

from pydantic import BaseModel, SecretStr

from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.model_defaults import PresetName


class ApiKeyIn(BaseModel):
    provider: str
    key: SecretStr


class ApiKeyOut(BaseModel):
    """A key, never in clear text: only the last 4 characters are exposed."""

    provider: str
    label: str
    source: Literal["ui", "env"] | None
    last4: str | None
    readable: bool
    last_tested_at: datetime | None
    last_test_ok: bool | None


class ProviderModels(BaseModel):
    name: str
    label: str
    has_key: bool
    # `None`: provider without a list, key missing or unreadable, or list unavailable.
    models: list[str] | None


class ModelsOut(BaseModel):
    providers: list[ProviderModels]
    presets: dict[PresetName, dict[Tier, ModelChoice]]

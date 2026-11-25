"""User settings the engine needs for a run.

The engine does not read the `settings` feature (import contract: `app.agents` never imports
`app.features`): the composition (`app.bootstrap`) provides it with a `RunSettingsSource`, adapted
from the settings service, like the model factory and the price table.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RunSettings:
    session_token_cap: int  # token cap per session (SPEC 9.3, 11.4)
    debate_rounds: int
    lesson_language: str
    search_languages: tuple[str, ...]
    style_guide: str


class RunSettingsSource(Protocol):
    async def get_run_settings(self, user_id: str) -> RunSettings: ...

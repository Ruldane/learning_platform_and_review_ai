"""Les noms d'agents du fil (écrits par le code) suivent la liste du front (`agents.ts`) et couvrent
chaque agent du moteur : une dérive casse ce test au lieu d'afficher « Un agent »."""

import re
from pathlib import Path

import pytest

from app.agents.registry import AGENTS
from app.features.activity.service.sources import AGENT_NAMES

FRONT_AGENTS = (
    Path(__file__).resolve().parents[4]
    / "frontend"
    / "src"
    / "shared"
    / "i18n"
    / "messages"
    / "agents.ts"
)
ENTRY = re.compile(r'^\s+(\w+): \{ name: "([^"]+)"', re.MULTILINE)


def test_every_engine_agent_has_a_name() -> None:
    assert set(AGENTS) <= set(AGENT_NAMES)


def test_names_match_the_front_list() -> None:
    if not FRONT_AGENTS.exists():
        pytest.skip("front absent (image du back)")
    front = dict(ENTRY.findall(FRONT_AGENTS.read_text(encoding="utf-8")))
    assert front, "agents.ts illisible"
    assert set(AGENT_NAMES) == set(front)
    for slug, name in front.items():
        assert AGENT_NAMES[slug] == name, slug

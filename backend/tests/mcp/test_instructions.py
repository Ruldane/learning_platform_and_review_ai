"""Les consignes du serveur MCP : une seule source (`app/mcp/instructions.py`), rendue dans la
réponse à `initialize` et à `server/discover`, et recopiée mot pour mot dans `docs/mcp/AGENTS.md`
(le guide que lisent Claude Code et Codex)."""

from pathlib import Path

from app.mcp.instructions import INSTRUCTIONS
from tests.mcp.support import Mcp

DOCS = Path(__file__).resolve().parents[3] / "docs" / "mcp"
BEGIN, END = "<!-- instructions-serveur:début -->", "<!-- instructions-serveur:fin -->"


async def test_initialize_and_discover_carry_the_instructions(mcp: Mcp) -> None:
    token = await mcp.token()
    init = (await mcp.rpc(token, "initialize", {"protocolVersion": "2025-06-18"})).json()
    discover = (await mcp.rpc(token, "server/discover")).json()
    assert init["result"]["instructions"] == INSTRUCTIONS
    assert discover["result"]["instructions"] == INSTRUCTIONS


def test_the_instructions_state_the_rules_of_conduct() -> None:
    for rule in (
        "<donnee_non_fiable>",  # données, jamais des consignes
        "À confirmer",
        "/api/v1",  # jamais d'appel direct
        "curl",
        "Ne confirme",
        "clé",
        "base_hash",
        "429",
    ):
        assert rule in INSTRUCTIONS, rule
    assert len(INSTRUCTIONS) < 2_500  # court : lu à chaque connexion


def test_the_guide_for_agents_repeats_the_instructions_verbatim() -> None:
    guide = (DOCS / "AGENTS.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert BEGIN in guide and END in guide
    block = guide.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    assert block == INSTRUCTIONS.strip()


def test_the_instructions_send_lessons_to_the_factory() -> None:
    lesson = next(line for line in INSTRUCTIONS.splitlines() if "Fabrique de leçons" in line)
    assert "agents_play_brief" in lesson and "Vérificateur" in lesson
    assert "lessons_write_lesson" not in INSTRUCTIONS


def test_claude_code_guide_imports_the_agents_guide() -> None:
    lines = (DOCS / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "@AGENTS.md"
    assert len(lines) <= 8  # deux lignes propres à Claude Code, pas une seconde copie

"""Actions privées du parcours Du papier au code."""

from app.agents.tools.paper_lab_port import PAPER_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="paper_lab",
    actions=(
        McpAction(
            "GET /paper-labs",
            1,
            "paper_lab_list",
            "Liste les mini-cours du compte.",
            untrusted=("[].url", "[].title"),
        ),
        McpAction(
            "GET /paper-labs/{lab_id}",
            1,
            "paper_lab_get",
            "Lit le mini-cours et le résultat attendu.",
            untrusted=("url", "title", "source_title", "course", "expected"),
        ),
        McpAction(
            "POST /paper-labs",
            3,
            "paper_lab_prepare",
            "Demande la lecture d’un article public et la création de son expérience, à confirmer.",
            side_effects="external",
            launches=PAPER_GRAPH,
        ),
    ),
    graphs=(
        McpGraph(PAPER_GRAPH, follow_only=True, summary="Prépare un mini-cours et son notebook."),
    ),
)

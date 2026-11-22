from app.agents.tools.blind_assessment_port import BLIND_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_RESULT = ("result.feedback", "result.source_a.label", "result.source_b.label")

MCP = FeatureMcp(
    feature="blind_assessment",
    actions=(
        McpAction(
            "GET /blind-assessments/options",
            1,
            "blind_assessment_options",
            "Liste les versions de CV détenues et les grilles.",
            untrusted=("sources[].label",),
        ),
        McpAction(
            "GET /blind-assessments",
            1,
            "blind_assessment_list",
            "Relit les épreuves en aveugle du compte.",
            untrusted=tuple(f"[].{path}" for path in _RESULT),
        ),
        McpAction(
            "GET /blind-assessments/{assessment_id}",
            1,
            "blind_assessment_read",
            "Relit le verdict et les sources si l’évaluation est terminée.",
            untrusted=_RESULT,
        ),
        McpAction(
            "POST /blind-assessments",
            2,
            "blind_assessment_create",
            "Fige deux CV et une grille dans une épreuve en aveugle.",
        ),
        McpAction(
            "POST /blind-assessments/{assessment_id}/evaluate",
            3,
            "blind_assessment_evaluate",
            "Demande de confirmer l’envoi des deux textes anonymisés au Vérificateur.",
            side_effects="external",
            launches=BLIND_GRAPH,
        ),
    ),
    graphs=(McpGraph(BLIND_GRAPH, follow_only=True),),
)

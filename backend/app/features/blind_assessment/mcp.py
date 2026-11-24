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
            "Lists the owned CV versions and the rubrics.",
            untrusted=("sources[].label",),
        ),
        McpAction(
            "GET /blind-assessments",
            1,
            "blind_assessment_list",
            "Reads the account's blind assessments.",
            untrusted=tuple(f"[].{path}" for path in _RESULT),
        ),
        McpAction(
            "GET /blind-assessments/{assessment_id}",
            1,
            "blind_assessment_read",
            "Reads the verdict and the sources once the assessment is finished.",
            untrusted=_RESULT,
        ),
        McpAction(
            "POST /blind-assessments",
            2,
            "blind_assessment_create",
            "Freezes two CVs and a rubric into a blind assessment.",
        ),
        McpAction(
            "POST /blind-assessments/{assessment_id}/evaluate",
            3,
            "blind_assessment_evaluate",
            "Asks to confirm sending the two anonymized texts to the Verifier.",
            side_effects="external",
            launches=BLIND_GRAPH,
        ),
    ),
    graphs=(McpGraph(BLIND_GRAPH, follow_only=True),),
)

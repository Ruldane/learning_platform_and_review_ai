from app.agents.tools.code_trial_port import GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_ROOT = "/ide/sessions/{session_id}/code-trials"
_UNTRUSTED = (
    "title",
    "pleadings[].argument",
    "pleadings[].citations[].path",
    "pleadings[].citations[].text",
    "verdict.reason",
)

MCP = FeatureMcp(
    feature="code_trial",
    actions=(
        McpAction(
            f"GET {_ROOT}",
            1,
            "code_trial_read_latest",
            "Reads the project's latest trial and its cited passages.",
            untrusted=_UNTRUSTED,
        ),
        McpAction(
            f"GET {_ROOT}/{{trial_id}}",
            1,
            "code_trial_read_dossier",
            "Reads a project trial, its pleadings and any verdict.",
            untrusted=_UNTRUSTED,
        ),
        McpAction(
            f"POST {_ROOT}",
            3,
            "code_trial_open_dossier",
            "Freezes the project version and runs the pleadings on OpenAI. Requires confirmation.",
            side_effects="external",
            launches=GRAPH,
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/code-trials/{trial_id}/verdict",
            3,
            "code_trial_judge_code_trial",
            "Records the personal verdict on the trial. Requires confirmation.",
        ),
    ),
    graphs=(McpGraph(GRAPH, follow_only=True),),
)

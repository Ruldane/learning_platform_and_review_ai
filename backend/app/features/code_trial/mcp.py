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
            "Lit le dernier procès du projet et ses passages cités.",
            untrusted=_UNTRUSTED,
        ),
        McpAction(
            f"GET {_ROOT}/{{trial_id}}",
            1,
            "code_trial_read_dossier",
            "Lit un procès du projet, les plaidoiries et le verdict éventuel.",
            untrusted=_UNTRUSTED,
        ),
        McpAction(
            f"POST {_ROOT}",
            3,
            "code_trial_open_dossier",
            "Fige la version du projet et lance les plaidoiries sur OpenAI. À confirmer.",
            side_effects="external",
            launches=GRAPH,
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/code-trials/{trial_id}/verdict",
            3,
            "code_trial_judge_code_trial",
            "Enregistre le verdict personnel sur l’essai. Demande à confirmer.",
        ),
    ),
    graphs=(McpGraph(GRAPH, follow_only=True),),
)

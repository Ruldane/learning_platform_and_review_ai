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
    ),
    excluded={
        f"PUT {_ROOT}/{{trial_id}}/verdict": "Le verdict est un geste personnel dans l’interface."
    },
    graphs=(McpGraph(GRAPH, follow_only=True),),
)

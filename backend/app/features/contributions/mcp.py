from app.mcp.base import FeatureMcp, McpAction

_ROOT = "/contributions"
_ONE = _ROOT + "/{contribution_id}"
_DOSSIER_FIELDS = (
    "issue.title",
    "issue.body",
    "issue.url",
    "publication_url",
    "pull_url",
    "cv_line",
)

MCP = FeatureMcp(
    feature="contributions",
    actions=(
        McpAction(
            f"GET {_ROOT}/suggestions",
            1,
            "contributions_list_suggestions",
            "Public issues for the program's current chapter.",
            untrusted=("items[].title", "items[].body", "items[].url"),
        ),
        McpAction(
            f"GET {_ROOT}",
            1,
            "contributions_list_dossiers",
            "The user's contribution files.",
            untrusted=tuple(f"[].{field}" for field in _DOSSIER_FIELDS),
        ),
        McpAction(
            f"GET {_ONE}",
            1,
            "contributions_read_dossier",
            "Reads the contribution file and its pull request, if any.",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ROOT}",
            3,
            "contributions_create_dossier",
            "Creates a contribution file from a program issue. Asks for confirmation.",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ONE}/publication",
            3,
            "contributions_prepare_publication",
            "Prepares the GitHub publication link with the text and branches. Asks for "
            "confirmation.",
            side_effects="external",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ONE}/pull",
            3,
            "contributions_track_pull",
            "Checks the pull request and links it to its file. Asks for confirmation.",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ONE}/refresh",
            3,
            "contributions_refresh_pull",
            "Rereads the pull request and records the proof after merge. Asks for confirmation.",
            untrusted=_DOSSIER_FIELDS,
        ),
    ),
)

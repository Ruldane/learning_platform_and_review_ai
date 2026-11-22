from app.mcp.base import FeatureMcp, McpAction

_TEXT = (
    "posting_title",
    "company",
    "criteria[].text",
    "criteria[].skills[]",
    "criteria[].note",
    "submission.artifact",
)

MCP = FeatureMcp(
    feature="missions",
    actions=(
        McpAction(
            "GET /missions",
            1,
            "missions_list_missions",
            "Liste les missions de 48 heures.",
            untrusted=tuple(f"[].{field}" for field in _TEXT),
        ),
        McpAction(
            "GET /missions/{mission_id}",
            1,
            "missions_get_mission",
            "Lit une mission, ses mesures et sa preuve de rendu.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /missions",
            2,
            "missions_start_mission",
            "Crée une mission sur une offre analysée à partir d'une à trois exigences choisies.",
            untrusted=_TEXT,
        ),
        McpAction(
            "PATCH /missions/{mission_id}/criteria/{index}",
            2,
            "missions_update_criterion",
            "Enregistre le nombre de cas validés et la note choisie pour un critère.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /missions/{mission_id}/submission",
            2,
            "missions_submit_mission",
            "Enregistre en privé le rendu et sa preuve une fois tous les cas validés.",
            untrusted=_TEXT,
        ),
    ),
)

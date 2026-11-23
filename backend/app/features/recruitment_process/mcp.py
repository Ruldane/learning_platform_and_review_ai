from app.mcp.base import FeatureMcp, McpAction, McpGraph

_ANSWER = "POST /recruitment-processes/{process_id}/steps/{kind}/answers"
_TEXT = (
    "posting_title",
    "company",
    "project.title",
    "missing_proofs[].requirement",
    "missing_proofs[].skills[]",
    "steps[].prompt",
    "steps[].answer",
    "steps[].grade.feedback",
)

MCP = FeatureMcp(
    feature="recruitment_process",
    actions=(
        McpAction(
            "GET /recruitment-processes/options",
            1,
            "recruitment_process_options",
            "Liste les offres analysées et projets revus du compte.",
            untrusted=("postings[].title", "projects[].title"),
        ),
        McpAction(
            "GET /recruitment-processes",
            1,
            "recruitment_process_list",
            "Liste les répétitions de recrutement du compte.",
            untrusted=tuple(f"[].{path}" for path in _TEXT),
        ),
        McpAction(
            "GET /recruitment-processes/{process_id}",
            1,
            "recruitment_process_read",
            "Relit la grille, les preuves manquantes et les résultats.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /recruitment-processes",
            2,
            "recruitment_process_create",
            "Prépare une répétition privée à partir d’une offre analysée.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /recruitment-processes/{process_id}/steps/{kind}/answers",
            3,
            "recruitment_process_submit_step_answer",
            "Remet une réponse de la répétition d’entretien. Demande à confirmer.",
            launches="recruitment_process",
        ),
    ),
    graphs=(McpGraph("recruitment_process", follow_only=True),),
)

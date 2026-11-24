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
            "Lists the account's analyzed postings and reviewed projects.",
            untrusted=("postings[].title", "projects[].title"),
        ),
        McpAction(
            "GET /recruitment-processes",
            1,
            "recruitment_process_list",
            "Lists the account's recruitment rehearsals.",
            untrusted=tuple(f"[].{path}" for path in _TEXT),
        ),
        McpAction(
            "GET /recruitment-processes/{process_id}",
            1,
            "recruitment_process_read",
            "Reads the rubric, the missing proofs and the results.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /recruitment-processes",
            2,
            "recruitment_process_create",
            "Prepares a private rehearsal from an analyzed posting.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /recruitment-processes/{process_id}/steps/{kind}/answers",
            3,
            "recruitment_process_submit_step_answer",
            "Submits an answer to the interview rehearsal. Asks for confirmation.",
            launches="recruitment_process",
        ),
    ),
    graphs=(McpGraph("recruitment_process", follow_only=True),),
)

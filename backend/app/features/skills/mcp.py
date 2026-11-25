"""MCP declaration for the skill map and for creating reference-data entries."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="skills",
    actions=(
        McpAction(
            "POST /skills",
            2,
            "skills_write_skill",
            "Adds a skill to the catalog, without assigning a level or proof.",
        ),
        McpAction(
            "GET /skills/graph",
            1,
            "skills_get_graph",
            "Skills, prerequisites and radar by domain.",
        ),
        McpAction(
            "GET /skills/compare",
            1,
            "skills_compare_skills",
            "Compares January's skills with the target role or a posting.",
        ),
        McpAction(
            "GET /skills/history",
            1,
            "skills_get_history",
            "Weekly snapshots of the skill map.",
        ),
        McpAction(
            "GET /skills/{skill_id}",
            1,
            "skills_get_skill",
            "A skill's details: proofs, postings that cite it, next action.",
        ),
    ),
)

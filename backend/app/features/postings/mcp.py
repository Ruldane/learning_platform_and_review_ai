"""MCP declaration for `postings`: add a posting (link or text), read it, remove it.

The text of a posting comes from the web: anything the response quotes from it is returned as
data, never as an instruction."""

from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "company", "text", "url", "analysis", "duplicates")

MCP = FeatureMcp(
    feature="postings",
    actions=(
        McpAction(
            "POST /postings",
            2,
            "postings_add_posting",
            "Adds a job posting by its link (`url`) or pasted text (`text`) and starts "
            "the analysis; the same posting returns the existing one.",
            untrusted=tuple(f"posting.{name}" for name in _TEXT),
            launches="gap_analysis",
        ),
        McpAction(
            "GET /postings",
            1,
            "postings_list_postings",
            "January's job postings, most recent first.",
            untrusted=("[].title", "[].company"),
        ),
        McpAction(
            "GET /postings/{posting_id}",
            1,
            "postings_get_posting",
            "A job posting: frozen text, analysis, duplicates.",
            untrusted=_TEXT,
        ),
        McpAction(
            "DELETE /postings/{posting_id}",
            3,
            "postings_delete_posting",
            "Removes the posting, its memory item, its reviews and its CV versions (PDFs and "
            "images included): asks for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "POST /postings/{posting_id}/distinct",
            2,
            "postings_mark_distinct",
            "Marks two postings as distinct: the duplicate disappears on both sides.",
        ),
        McpAction(
            "POST /postings/{posting_id}/gap",
            2,
            "postings_relaunch_gap",
            "Restarts the gap analysis of a posting.",
            launches="gap_analysis",
        ),
        McpAction(
            "POST /postings/direct",
            2,
            "postings_write_posting",
            "Direct write, no agent: stores a posting Claude has read (`text`: at least 300 "
            "characters and 50 words, optional `url`, and its analysis: `title`, "
            "`company`, `requirements`, `keywords`, "
            "`skills`…); the posting is ready at once, without a gap (`postings_relaunch_gap`).",
            untrusted=tuple(f"posting.{name}" for name in _TEXT),
        ),
        McpAction(
            "PATCH /postings/{posting_id}",
            2,
            "postings_update_posting",
            "Direct write, no agent: edits the analysis of a posting (title, company, "
            "requirements, keywords, skills…).",
            untrusted=_TEXT,
        ),
    ),
)

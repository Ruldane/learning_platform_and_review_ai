from hashlib import sha256
from textwrap import indent

from app.features.project_handoffs.schemas import (
    ProjectHandoffDraft,
    ProjectHandoffPreview,
    ProjectHandoffSource,
)


def _literal(text: str) -> str:
    return indent("\n".join(text.splitlines()), "    ")


def preview_guide(
    source: ProjectHandoffSource, draft: ProjectHandoffDraft
) -> ProjectHandoffPreview:
    """The submission and the notes are literal text, in indented Markdown blocks."""
    parts = [
        "# Handoff guide",
        "## Project",
        _literal(source.project_title),
        f"Project identifier `{source.project_id}`",
        f"Submitted on `{source.submitted_at.isoformat()}`",
    ]
    if source.description:
        parts += ["## Existing submission", _literal(source.description)]
    if source.repo_url:
        parts += ["## Submission repository", _literal(source.repo_url)]
    parts += [
        "## Acceptance commands",
        _literal(draft.commands),
        "## Known limitations",
        _literal(draft.limitations),
        "## Getting started steps",
        _literal(draft.steps),
    ]
    markdown = "\n\n".join(parts) + "\n"
    return ProjectHandoffPreview(
        digest=sha256(markdown.encode("utf-8")).hexdigest(), markdown=markdown
    )

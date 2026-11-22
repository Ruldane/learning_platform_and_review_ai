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
    """Le rendu et les notes sont du texte littéral, dans des blocs Markdown indentés."""
    parts = [
        "# Guide de reprise",
        "## Projet",
        _literal(source.project_title),
        f"Identifiant du projet `{source.project_id}`",
        f"Rendu du `{source.submitted_at.isoformat()}`",
    ]
    if source.description:
        parts += ["## Rendu existant", _literal(source.description)]
    if source.repo_url:
        parts += ["## Dépôt du rendu", _literal(source.repo_url)]
    parts += [
        "## Commandes de recette",
        _literal(draft.commands),
        "## Limites connues",
        _literal(draft.limitations),
        "## Étapes de prise en main",
        _literal(draft.steps),
    ]
    markdown = "\n\n".join(parts) + "\n"
    return ProjectHandoffPreview(
        digest=sha256(markdown.encode("utf-8")).hexdigest(), markdown=markdown
    )

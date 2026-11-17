"""Déclaration MCP de `projects` : le Portfolio des mini projets preuves.

Le rendu d'un projet (`POST /projects/{id}/submit`) est un formulaire multipart : le MCP l'envoie
avec le lien et la description (`encoding="form"`), jamais de capture. L'entrée au profil maître
est de niveau 3, avec un contrôle préalable des chiffres."""

from pydantic import ValidationError

from app.agents.tools.cv_lexicon import figures_in
from app.features.projects.schemas import ProfileEntryIn
from app.mcp.base import FeatureMcp, McpAction, McpGraph, PrecheckInput, Verdict


async def profile_entry_precheck(request: PrecheckInput) -> Verdict:
    """Un chiffre des réalisations que ni le nom ni la description ne disent est signalé (sans le
    recopier) : January le vérifie avant que le projet n'entre au profil maître."""
    try:
        body = ProfileEntryIn.model_validate(request.body)
    except ValidationError:
        return Verdict(
            ok=False,
            reasons=("L'entrée de projet n'est pas lisible : la route la refusera.",),
            summary="Ajout d'un projet validé au profil maître (contenu illisible).",
        )
    known = figures_in(f"{body.name} {body.description}")
    unknown = {figure for line in body.achievements for figure in figures_in(line)} - known
    reasons = (
        (f"{len(unknown)} chiffre(s) des réalisations absent(s) de la description du projet.",)
        if unknown
        else ()
    )
    summary = (
        f"Ajout d'un projet validé au profil maître ({len(body.achievements)} réalisation(s))."
    )
    return Verdict(ok=not reasons, reasons=reasons, summary=summary)


MCP = FeatureMcp(
    feature="projects",
    actions=(
        McpAction(
            "GET /projects",
            1,
            "projects_list_projects",
            "Le Portfolio : projets, programme, semaine et rang ; `status` filtre.",
        ),
        McpAction(
            "GET /projects/{project_id}",
            1,
            "projects_get_project",
            "Un projet : énoncé, rendus, évaluation, brouillons.",
        ),
        McpAction(
            "PATCH /projects/{project_id}/drafts/{kind}",
            2,
            "projects_update_draft",
            "Retouche un brouillon (`entry` ou `content`) ; un brouillon « à vérifier » est relu.",
        ),
        McpAction(
            "POST /projects/{project_id}/profile-entry",
            3,
            "projects_add_profile_entry",
            "Ajoute le projet validé au profil maître (nouvelle version validée) : écriture au "
            "profil, demande à confirmer, avec contrôle des chiffres.",
            side_effects="external",
            precheck=profile_entry_precheck,
        ),
        McpAction(
            "POST /projects/{project_id}/brief",
            2,
            "projects_retry_brief",
            "Relance l'énoncé d'un projet dont les trois essais ont échoué.",
            launches="project_brief",
        ),
        McpAction(
            "POST /projects/{project_id}/drafts",
            2,
            "projects_retry_drafts",
            "Relance les brouillons d'un projet validé qui n'en a pas.",
            launches="project_review",
        ),
        McpAction(
            "POST /projects/{project_id}/submit",
            2,
            "projects_submit_project",
            "Rend le projet : un lien (`repo_url`) et/ou une description (4 000 caractères au "
            "plus), sans capture. L'évaluation se lance ; suis la session.",
            encoding="form",
            launches="project_review",
        ),
        McpAction(
            "POST /projects",
            2,
            "projects_write_project",
            "Écriture directe, aucun agent : écrit le mini projet d'un module (`module_id`, "
            "`brief` : titre, contexte, objectif, contraintes, critères, heures, livrable) ; "
            "le projet est à faire.",
        ),
        McpAction(
            "PATCH /projects/{project_id}",
            2,
            "projects_update_project",
            "Écriture directe, aucun agent : retouche l'énoncé d'un projet qui n'a pas encore "
            "de rendu.",
        ),
    ),
    graphs=(
        McpGraph(
            "project_brief", follow_only=True, summary="Écrit l'énoncé d'un projet (`project_id`)."
        ),
        McpGraph(
            "project_review",
            follow_only=True,
            summary="Évalue le rendu d'un projet (`project_id`, `mode` review ou drafts).",
            untrusted=("result",),
        ),
    ),
    excluded={
        "GET /projects/{project_id}/screenshots/{number}": (
            "Image d'une capture (binaire, pas du JSON) : visible dans le Portfolio de l'interface."
        ),
    },
)

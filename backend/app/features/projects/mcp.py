"""Déclaration MCP de `projects` : le Portfolio des mini projets preuves.

Le rendu d'un projet exige une confirmation dans Tremplin. L'entrée au profil maître exige
également un contrôle préalable des chiffres."""

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
            reasons=("The project entry is unreadable: the route will reject it.",),
            summary="Adding a validated project to the master profile (unreadable content).",
        )
    known = figures_in(f"{body.name} {body.description}")
    unknown = {figure for line in body.achievements for figure in figures_in(line)} - known
    reasons = (
        (f"{len(unknown)} achievement figure(s) missing from the project description.",)
        if unknown
        else ()
    )
    summary = (
        f"Adding a validated project to the master profile ({len(body.achievements)} "
        "achievement(s)."
    )
    return Verdict(ok=not reasons, reasons=reasons, summary=summary)


MCP = FeatureMcp(
    feature="projects",
    actions=(
        McpAction(
            "GET /projects",
            1,
            "projects_list_projects",
            "The Portfolio: projects, program, week and rank; `status` filters.",
        ),
        McpAction(
            "GET /projects/{project_id}",
            1,
            "projects_get_project",
            "A project: brief, submissions, evaluation, drafts.",
        ),
        McpAction(
            "GET /projects/{project_id}/github-claims",
            1,
            "projects_list_verified_github_commits",
            "Lists the public commits whose authorship the project has verified.",
            untrusted=("[].commit_url",),
        ),
        McpAction(
            "PATCH /projects/{project_id}/drafts/{kind}",
            2,
            "projects_update_draft",
            'Edits a draft (`entry` or `content`); a draft marked "to check" is reviewed.',
        ),
        McpAction(
            "POST /projects/{project_id}/profile-entry",
            3,
            "projects_add_profile_entry",
            "Adds the validated project to the master profile (new validated version): a profile "
            "write that needs confirmation, with a check of the figures.",
            side_effects="external",
            precheck=profile_entry_precheck,
        ),
        McpAction(
            "POST /projects/{project_id}/brief",
            2,
            "projects_retry_brief",
            "Retries the brief of a project whose three attempts failed.",
            launches="project_brief",
        ),
        McpAction(
            "POST /projects/{project_id}/drafts",
            2,
            "projects_retry_drafts",
            "Retries the drafts of a validated project that has none.",
            launches="project_review",
        ),
        McpAction(
            "POST /projects",
            2,
            "projects_write_project",
            "Direct write, no agent: writes the mini project of a module (`module_id`, "
            "`brief`: title, context, objective, constraints, criteria, hours, deliverable); "
            "the project is set to do.",
        ),
        McpAction(
            "PATCH /projects/{project_id}",
            2,
            "projects_update_project",
            "Direct write, no agent: edits the brief of a project that has no submission yet.",
        ),
        McpAction(
            "POST /projects/{project_id}/github-claims",
            3,
            "projects_start_github_claim",
            "Prepares the GitHub verification challenge. Needs confirmation.",
        ),
        McpAction(
            "POST /projects/{project_id}/submit",
            3,
            "projects_submit_project",
            "Submits the project from a link or a text. Needs confirmation.",
            encoding="form",
            launches="project_review",
        ),
        McpAction(
            "GET /projects/{project_id}/screenshots/{number}",
            1,
            "projects_get_project_screenshot",
            "Reads the metadata of a screenshot and gives its local link.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph(
            "project_brief",
            follow_only=True,
            summary="Writes the brief of a project (`project_id`).",
        ),
        McpGraph(
            "project_review",
            follow_only=True,
            summary="Evaluates a project submission (`project_id`, `mode` review or drafts).",
            untrusted=("result",),
        ),
    ),
)

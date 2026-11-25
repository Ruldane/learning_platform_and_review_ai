"""MCP declaration for `cv`: master profile, templates, CV reviews and versions.

The master profile is never written without January: `PUT /profile` and the confirmation of a
fact (`PATCH /cv/modifications/{id}`) are level 3 and carry a prior check (`precheck`), whose
verdict is shown on the "To confirm" card. PDFs and images, and PDF uploads, are excluded
(not JSON)."""

from pydantic import ValidationError

from app.agents.tools.cv_schema import MasterProfileData
from app.features.cv.schemas_profile import ProfilePutIn
from app.mcp.base import FeatureMcp, McpAction, McpGraph, PrecheckInput, Verdict

# Sources that come from a January document; "january": written by hand (or by
# Claude), with no document behind it.
DOCUMENT_SOURCES = frozenset({"cv", "linkedin", "note"})

_SECTIONS = (
    ("experiences", "experience(s)"),
    ("education", "education entry(ies)"),
    ("skills", "skill(s)"),
    ("projects", "project(s)"),
    ("languages", "language(s)"),
    ("links", "link(s)"),
)


def unsourced_counts(data: MasterProfileData) -> dict[str, int]:
    """Per section, the facts that no January document backs (source "january" only, or none):
    what the profile owes to a hand-written entry. Never the text of the facts."""
    counts: dict[str, int] = {}
    for line_name, label in (("title", "title"), ("summary", "summary")):
        line = getattr(data, line_name)
        if line is not None and not DOCUMENT_SOURCES & set(line.sources):
            counts[label] = 1
    for attribute, label in _SECTIONS:
        missing = sum(
            1 for fact in getattr(data, attribute) if not DOCUMENT_SOURCES & set(fact.sources)
        )
        if missing:
            counts[label] = missing
    return counts


async def profile_precheck(request: PrecheckInput) -> Verdict:
    """Honesty check of a new version of the master profile: each fact without a document
    source is flagged (without copying it). The check blocks nothing: January decides."""
    try:
        body = ProfilePutIn.model_validate(request.body)
    except ValidationError:
        return Verdict(
            ok=False,
            reasons=("The profile content is unreadable: the route will reject it.",),
            summary="New validated version of the master profile (unreadable content).",
        )
    counts = unsourced_counts(body.data)
    reasons = tuple(f"{n} {label} without a document source" for label, n in counts.items())
    summary = "New validated version of the master profile"
    if body.base_version is not None:
        summary += f", written from version {body.base_version}"
    return Verdict(ok=not reasons, reasons=reasons, summary=f"{summary}.")


async def modification_precheck(request: PrecheckInput) -> Verdict:
    """A decision on a CV modification only writes to the profile if `confirm` is true: the
    "to confirm" fact (number, tool or title the profile does not state) then enters it."""
    body = request.body if isinstance(request.body, dict) else {}
    if body.get("confirm") is True:
        return Verdict(
            ok=False,
            reasons=(
                "Confirming writes to the master profile a fact the current profile does not "
                "state: accept only if it is true.",
            ),
            summary='Confirms a "to confirm" modification: new profile version.',
        )
    return Verdict(ok=True, summary="Decision on a CV modification; nothing enters the profile.")


MCP = FeatureMcp(
    feature="cv",
    actions=(
        McpAction(
            "GET /profile", 1, "cv_get_profile", "The master profile: validated version and draft."
        ),
        McpAction(
            "PUT /profile",
            3,
            "cv_put_profile",
            "Writes a new validated version of the master profile (`data`, `base_version`). "
            "Profile write: asks for confirmation, with a check of unsourced facts.",
            side_effects="external",
            precheck=profile_precheck,
        ),
        McpAction(
            "GET /profile/versions", 1, "cv_list_profile_versions", "The master profile versions."
        ),
        McpAction("GET /cv/templates", 1, "cv_list_templates", "The non-archived CV templates."),
        McpAction(
            "GET /cv/templates/{template_id}",
            1,
            "cv_get_template",
            "A CV template, with its status and pages.",
        ),
        McpAction(
            "POST /cv/templates/{template_id}/activate",
            2,
            "cv_activate_template",
            "Makes this template the only active one.",
        ),
        McpAction(
            "DELETE /cv/templates/{template_id}",
            3,
            "cv_archive_template",
            "Archives a CV template: asks for confirmation.",
        ),
        McpAction(
            "POST /cv/reviews",
            2,
            "cv_start_review",
            "Starts the CV review against a posting (`posting_id`) with the validated profile and "
            "the active template.",
            launches="cv_review",
        ),
        McpAction(
            "GET /cv/reviews",
            1,
            "cv_list_reviews",
            "CV reviews (for a posting), newest first.",
        ),
        McpAction(
            "GET /cv/reviews/{review_id}",
            1,
            "cv_get_review",
            "A CV review: analysis, proposed modifications, decisions.",
        ),
        McpAction(
            "PATCH /cv/reviews/{review_id}/modifications",
            2,
            "cv_decide_modifications",
            "Accepts or rejects modifications in bulk (50 at most); 'to confirm' ones are "
            "never accepted in bulk.",
        ),
        McpAction(
            "PATCH /cv/modifications/{modification_id}",
            3,
            "cv_decide_modification",
            "Accepts or rejects a modification (`status`, `after`, `confirm`); `confirm` writes "
            "the fact to the master profile: asks for confirmation, with a precheck.",
            precheck=modification_precheck,
        ),
        McpAction(
            "POST /cv/reviews/{review_id}/generate",
            3,
            "cv_generate_version",
            "Creates the tailored CV version and produces its PDF and images (files): asks for "
            "confirmation.",
            side_effects="external",
        ),
        McpAction("GET /cv/versions", 1, "cv_list_versions", "The tailored CV versions."),
        McpAction(
            "GET /cv/versions/{version_id}",
            1,
            "cv_get_version",
            "A tailored CV version and its status.",
        ),
        McpAction(
            "GET /cv/templates/{template_id}/pages/{kind}/{number}",
            1,
            "cv_get_template_page",
            "Reads the metadata of a template page image and gives its local link.",
            artifact=True,
        ),
        McpAction(
            "GET /cv/versions/{version_id}/pages/{number}",
            1,
            "cv_get_version_page",
            "Reads the metadata of a CV page image and gives its local link.",
            artifact=True,
        ),
        McpAction(
            "GET /cv/versions/{version_id}/pdf",
            1,
            "cv_get_version_pdf",
            "Reads the metadata of the CV PDF and gives its local link.",
            artifact=True,
        ),
    ),
    graphs=(
        McpGraph(
            "cv_review",
            follow_only=True,
            summary="Review of a CV against a posting (`review_id` of an existing review).",
        ),
        McpGraph(
            "cv_capture",
            follow_only=True,
            summary="The Archivist extracts a profile draft (`mode` profile, `document_ids`) "
            "or a template design (`mode` design, `template_id`); January validates.",
        ),
    ),
    play_actions=(
        McpAction(
            "POST /profile/import",
            2,
            "cv_capture_profile",
            "Prepares a profile draft from a PDF stored in Tremplin.",
            body_fields=frozenset({"cv_document_id", "linkedin_document_id", "note"}),
            encoding="form",
            launches="cv_capture",
        ),
        McpAction(
            "POST /cv/templates",
            2,
            "cv_capture_design",
            "Analyzes the images of a PDF stored in Tremplin to create a template from it.",
            body_fields=frozenset({"document_id", "name"}),
            encoding="form",
            launches="cv_capture",
        ),
    ),
)

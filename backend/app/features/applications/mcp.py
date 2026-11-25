"""Déclaration MCP de `applications` (six routeurs : fiches, kit, entretiens blancs, comité,
relances) : le suivi des candidatures. Rien n'est envoyé par l'application : « envoyer » une
candidature est un geste de January hors de l'application, le MCP note seulement l'événement."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_FILE = (
    "ZIP archive to download (binary, not JSON): January downloads it from the "
    "interface; the MCP reads the items through `applications_get_kit`."
)

MCP = FeatureMcp(
    feature="applications",
    actions=(
        McpAction(
            "GET /applications",
            1,
            "applications_list_applications",
            "The application records, filterable by status and by posting.",
        ),
        McpAction(
            "POST /applications",
            2,
            "applications_create_application",
            "Creates an application record by hand or from a posting (`posting_id`).",
            untrusted=("application.posting_text",),
        ),
        McpAction(
            "POST /applications/intake",
            2,
            "applications_start_intake",
            "Starts the Tracking Assistant on a sentence; January confirms the record before it "
            "is created.",
            launches="application_intake",
        ),
        McpAction(
            "GET /applications/check",
            1,
            "applications_check_posting",
            "Checks an incoming posting (duplicates) by `posting_id` or `url`.",
        ),
        McpAction(
            "GET /applications/stats",
            1,
            "applications_get_stats",
            "Records by status, response rate and delay, due follow-ups.",
        ),
        McpAction(
            "GET /applications/{application_id}",
            1,
            "applications_get_application",
            "A record: contacts, events, follow-ups, posting text.",
            untrusted=("company", "title", "posting_text"),
        ),
        McpAction(
            "PATCH /applications/{application_id}",
            2,
            "applications_update_application",
            "Edits a record; `contacts` replaces the contact list; the status only changes "
            "through `applications_add_event`.",
            untrusted=("posting_text",),
        ),
        McpAction(
            "POST /applications/{application_id}/events",
            2,
            "applications_add_event",
            "Changes a record's status or adds a dated note to it.",
            untrusted=("posting_text",),
        ),
        McpAction(
            "POST /applications/{application_id}/kit",
            2,
            "applications_start_kit",
            "Starts the seven items of the application kit; items edited by January are kept.",
            launches="application_kit",
        ),
        McpAction(
            "GET /applications/{application_id}/kit",
            1,
            "applications_get_kit",
            "The seven kit items, in their fixed order.",
        ),
        McpAction(
            "PATCH /applications/{application_id}/kit/{kind}",
            2,
            "applications_update_kit_item",
            "Replaces the text of a kit item; an item marked 'to check' is reviewed again.",
        ),
        McpAction(
            "POST /applications/{application_id}/interviews",
            2,
            "applications_start_application_interview",
            "Starts the mock interview for a record; questions arrive through the session.",
            launches="interview",
        ),
        McpAction(
            "POST /interviews",
            2,
            "applications_start_free_interview",
            "Starts a free mock interview, on a posting (`posting_id`) or a job title (`role`).",
            body_fields=frozenset(
                {
                    "mode",
                    "duration_min",
                    "language",
                    "radar_role",
                    "radar_zone",
                    "posting_id",
                    "role",
                }
            ),
            launches="interview",
        ),
        McpAction(
            "GET /interviews",
            1,
            "applications_list_interviews",
            "Mock interviews (for a record), newest first.",
        ),
        McpAction(
            "GET /interviews/{interview_id}",
            1,
            "applications_get_interview",
            "A mock interview: exchanges, debrief, review cards.",
        ),
        McpAction(
            "POST /committee",
            2,
            "applications_start_committee",
            "Convenes the simulated hiring committee on a ready CV version.",
            launches="hiring_committee",
        ),
        McpAction(
            "GET /committee",
            1,
            "applications_list_committees",
            "Committee runs (for a posting), newest first.",
        ),
        McpAction(
            "GET /committee/{run_id}",
            1,
            "applications_get_committee",
            "A committee run: votes, verdict, objections, before and after.",
        ),
        McpAction(
            "GET /reminders",
            1,
            "applications_list_reminders",
            "Follow-ups (due ones by default), with their ready-to-copy draft.",
        ),
        McpAction(
            "PATCH /reminders/{reminder_id}",
            2,
            "applications_update_reminder",
            "Marks a follow-up as done (`done`), postponed by 3 days (`postpone`) or ignored "
            "(`ignore`); nothing is sent.",
        ),
        McpAction(
            "GET /applications/{application_id}/kit.zip",
            1,
            "applications_get_kit_archive",
            "Reads the archive metadata. Read the text with applications_get_kit.",
            artifact=True,
        ),
        McpAction(
            "GET /interviews/{interview_id}/design",
            1,
            "applications_read_interview_design",
            "Reads this interview's architecture board.",
            untrusted=("board.scene",),
        ),
        McpAction(
            "GET /system-design",
            1,
            "applications_read_current_design",
            "Reads the architecture board of the current interview.",
            untrusted=("board.scene",),
        ),
    ),
    graphs=(
        McpGraph(
            "application_intake",
            follow_only=True,
            summary="The Tracking Assistant reads a sentence (`text`) and prepares a record; "
            "January confirms it.",
        ),
        McpGraph(
            "application_kit",
            follow_only=True,
            summary="Writes the seven kit items of a record (`application_id`).",
        ),
        McpGraph(
            "interview",
            follow_only=True,
            summary="Mock interview (`interview_id` of an existing interview).",
        ),
        McpGraph(
            "hiring_committee",
            follow_only=True,
            summary="Simulated hiring committee (`run_id` of an existing run).",
        ),
    ),
)

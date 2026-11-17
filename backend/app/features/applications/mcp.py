"""Déclaration MCP de `applications` (six routeurs : fiches, kit, entretiens blancs, comité,
relances) : le suivi des candidatures. Rien n'est envoyé par l'application : « envoyer » une
candidature est un geste de January hors de l'application, le MCP note seulement l'événement."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_FILE = (
    "Archive ZIP à télécharger (binaire, pas du JSON) : January la télécharge depuis "
    "l'interface ; le MCP lit les pièces par `applications_get_kit`."
)

MCP = FeatureMcp(
    feature="applications",
    actions=(
        McpAction(
            "GET /applications",
            1,
            "applications_list_applications",
            "Les fiches de candidature, filtrables par statut et par offre.",
        ),
        McpAction(
            "POST /applications",
            2,
            "applications_create_application",
            "Crée une fiche de candidature à la main ou depuis une offre (`posting_id`).",
            untrusted=("application.posting_text",),
        ),
        McpAction(
            "POST /applications/intake",
            2,
            "applications_start_intake",
            "Lance l'Assistant de suivi sur une phrase ; January confirme la fiche avant sa "
            "création.",
            launches="application_intake",
        ),
        McpAction(
            "GET /applications/check",
            1,
            "applications_check_posting",
            "Contrôle d'une offre qui entre (doublons) par `posting_id` ou `url`.",
        ),
        McpAction(
            "GET /applications/stats",
            1,
            "applications_get_stats",
            "Fiches par statut, taux et délai de réponse, relances dues.",
        ),
        McpAction(
            "GET /applications/{application_id}",
            1,
            "applications_get_application",
            "Une fiche : contacts, événements, relances, texte de l'offre.",
            untrusted=("company", "title", "posting_text"),
        ),
        McpAction(
            "PATCH /applications/{application_id}",
            2,
            "applications_update_application",
            "Retouche une fiche ; `contacts` remplace la liste des contacts ; le statut ne se "
            "change que par `applications_add_event`.",
            untrusted=("posting_text",),
        ),
        McpAction(
            "POST /applications/{application_id}/events",
            2,
            "applications_add_event",
            "Change le statut d'une fiche ou y ajoute une note, datée.",
            untrusted=("posting_text",),
        ),
        McpAction(
            "POST /applications/{application_id}/kit",
            2,
            "applications_start_kit",
            "Lance les sept pièces du kit de candidature ; les pièces modifiées par January "
            "sont gardées.",
            launches="application_kit",
        ),
        McpAction(
            "GET /applications/{application_id}/kit",
            1,
            "applications_get_kit",
            "Les sept pièces du kit, dans l'ordre fixe.",
        ),
        McpAction(
            "PATCH /applications/{application_id}/kit/{kind}",
            2,
            "applications_update_kit_item",
            "Remplace le texte d'une pièce du kit ; une pièce « à vérifier » est relue.",
        ),
        McpAction(
            "POST /applications/{application_id}/interviews",
            2,
            "applications_start_application_interview",
            "Lance l'entretien blanc d'une fiche ; les questions arrivent par la session.",
            launches="interview",
        ),
        McpAction(
            "POST /interviews",
            2,
            "applications_start_free_interview",
            "Lance un entretien blanc libre, sur une offre (`posting_id`) ou un intitulé (`role`).",
            launches="interview",
        ),
        McpAction(
            "GET /interviews",
            1,
            "applications_list_interviews",
            "Les entretiens blancs (d'une fiche), les plus récents d'abord.",
        ),
        McpAction(
            "GET /interviews/{interview_id}",
            1,
            "applications_get_interview",
            "Un entretien blanc : échanges, débrief, fiches de révision.",
        ),
        McpAction(
            "POST /committee",
            2,
            "applications_start_committee",
            "Réunit le comité de recrutement simulé sur une version de CV prête.",
            launches="hiring_committee",
        ),
        McpAction(
            "GET /committee",
            1,
            "applications_list_committees",
            "Les exécutions du comité (d'une offre), les plus récentes d'abord.",
        ),
        McpAction(
            "GET /committee/{run_id}",
            1,
            "applications_get_committee",
            "Une exécution du comité : votes, verdict, objections, avant et après.",
        ),
        McpAction(
            "GET /reminders",
            1,
            "applications_list_reminders",
            "Les relances (dues par défaut), avec leur brouillon prêt à copier.",
        ),
        McpAction(
            "PATCH /reminders/{reminder_id}",
            2,
            "applications_update_reminder",
            "Marque une relance faite (`done`), reportée de 3 jours (`postpone`) ou ignorée "
            "(`ignore`) ; rien n'est envoyé.",
        ),
    ),
    graphs=(
        McpGraph(
            "application_intake",
            follow_only=True,
            summary="L'Assistant de suivi lit une phrase (`text`) et prépare une fiche ; "
            "January la confirme.",
        ),
        McpGraph(
            "application_kit",
            follow_only=True,
            summary="Écrit les sept pièces du kit d'une fiche (`application_id`).",
        ),
        McpGraph(
            "interview",
            follow_only=True,
            summary="Entretien blanc (`interview_id` d'un entretien déjà créé).",
        ),
        McpGraph(
            "hiring_committee",
            follow_only=True,
            summary="Comité de recrutement simulé (`run_id` d'une exécution déjà créée).",
        ),
    ),
    excluded={"GET /applications/{application_id}/kit.zip": _FILE},
)

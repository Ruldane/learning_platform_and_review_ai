"""Déclaration MCP de `ide` : exercices, séances, exécutions et notes. Claude lit, lance le code et
écrit des notes. Il n'écrit dans les fichiers de January que si elle a allumé l'interrupteur
(`mcp_can_write_files`, réglé dans l'interface seulement, `ide_write_file`, annulable) ; sinon une
correction est une proposition qu'elle accepte dans l'interface. Il ne déclenche pas le professeur
interne (coût d'API : Claude écrit lui-même ses notes et ses exercices)."""

from app.mcp.base import FeatureMcp, McpAction

_GESTURE = (
    "Geste de January dans l'interface : jamais d'écriture directe dans son code par ce geste "
    "(une correction est une proposition qu'elle accepte ou refuse ; Claude écrit un fichier par "
    "`ide_write_file`, seulement si elle a allumé l'interrupteur)."
)
_COST = (
    "Coût d'API : Claude écrit lui-même ses notes (`ide_add_note`) et ses exercices "
    "(`ide_create_exercise`) au lieu de déclencher le professeur interne."
)

MCP = FeatureMcp(
    feature="ide",
    actions=(
        McpAction("GET /ide/exercises", 1, "ide_list_exercises", "Les exercices de l'IDE Python."),
        McpAction(
            "POST /ide/exercises",
            2,
            "ide_create_exercise",
            "Crée un exercice (titre, énoncé, fichiers de départ et tests).",
        ),
        McpAction(
            "DELETE /ide/exercises/{exercise_id}",
            3,
            "ide_delete_exercise",
            "Supprime un exercice : demande à confirmer.",
        ),
        McpAction("GET /ide/sessions", 1, "ide_list_sessions", "Les séances de code."),
        McpAction(
            "GET /ide/sessions/{session_id}",
            1,
            "ide_get_session",
            "Une séance : fichiers, exercice, dernière exécution.",
        ),
        McpAction(
            "POST /ide/sessions",
            2,
            "ide_create_session",
            "Ouvre une séance de code, libre ou sur un exercice.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/runs",
            2,
            "ide_start_run",
            "Exécute ou vérifie le code d'une séance dans le bac à sable (sans réseau).",
        ),
        McpAction(
            "GET /ide/runs/{run_id}",
            1,
            "ide_read_run",
            "Lit la sortie d'une exécution (`after` : décalage déjà lu).",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/notes",
            1,
            "ide_list_notes",
            "Les notes d'une séance : indices, explications, annotations, propositions.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/notes",
            2,
            "ide_add_note",
            "Écrit une note dans une séance : indice, explication, annotation ou proposition "
            "de correction (que January accepte ou refuse dans l'interface).",
        ),
        McpAction(
            "GET /ide/preferences",
            1,
            "ide_get_preferences",
            "Les préférences de l'IDE (mode du professeur, minuterie).",
        ),
        McpAction(
            "GET /ide/usage",
            1,
            "ide_get_usage",
            "La consommation du professeur : séance, jour, plafonds.",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/runs",
            1,
            "ide_list_runs",
            "Les 20 dernières exécutions d'une séance (celles de January et les tiennes), la plus "
            "récente d'abord.",
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/files",
            2,
            "ide_write_file",
            "Écrit UN fichier de la séance (le contenu entier). Seulement si January a allumé "
            "l'interrupteur « Claude peut écrire dans mes fichiers » (sinon 403 mcp_ide_write_off, "
            "propose alors une correction par une note). `base_hash` obligatoire : le sha256 du "
            "contenu actuel du fichier, donné par `file_hashes` dans `ide_get_session` (empreinte "
            "du texte vide pour un nouveau fichier). Si January a écrit depuis ta lecture : 409 "
            "stale_base, relis la séance. Annulable depuis « Accès MCP ».",
            body_fields=frozenset({"files", "base_hash"}),
        ),
    ),
    excluded={
        "POST /ide/notes/{note_id}/accept": _GESTURE,
        "POST /ide/notes/{note_id}/reject": _GESTURE,
        "POST /ide/sessions/{session_id}/teach": _COST,
        "POST /ide/exercises/generate": _COST,
        "PUT /ide/preferences": (
            "Préférences de l'IDE (mode du professeur, plafonds de coût, interrupteur d'écriture "
            "de Claude) : réservées à January dans l'interface, un agent ne règle ni son budget ni "
            "ses propres droits."
        ),
        "graph:ide_teacher": (
            "Lancé seulement par POST /ide/sessions/{session_id}/teach (exclue : coût de l'API de "
            "January). Claude fait ce travail lui-même par les notes "
            "(POST /ide/sessions/{session_id}/notes)."
        ),
        "graph:ide_exercise": (
            "Lancé seulement par POST /ide/exercises/generate (exclue : coût de l'API de "
            "January). Claude fait ce travail lui-même : il écrit ses exercices "
            "(POST /ide/exercises) et ses notes (POST /ide/sessions/{session_id}/notes)."
        ),
    },
)

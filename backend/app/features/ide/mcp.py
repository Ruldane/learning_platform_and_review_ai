"""Déclaration MCP de `ide` : exercices, séances, exécutions et notes. Claude lit, lance le code et
écrit des notes ; il n'écrit jamais dans le code de January (une correction est une proposition
qu'elle accepte dans l'interface) et ne déclenche pas le professeur interne (coût d'API : Claude
écrit lui-même ses notes et ses exercices)."""

from app.mcp.base import FeatureMcp, McpAction

_GESTURE = (
    "Geste de January dans l'interface : jamais d'écriture directe dans son code, ni par un "
    "agent ni par Claude (une correction est une proposition qu'elle accepte ou refuse)."
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
            "PATCH /ide/exercises/{exercise_id}",
            2,
            "ide_update_exercise",
            "Écriture directe, aucun agent ni exécution : retouche un exercice (titre, énoncé, "
            "fichiers de départ et de test pytest, fichier d'entrée).",
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
    ),
    excluded={
        "PUT /ide/sessions/{session_id}/files": _GESTURE,
        "POST /ide/notes/{note_id}/accept": _GESTURE,
        "POST /ide/notes/{note_id}/reject": _GESTURE,
        "POST /ide/sessions/{session_id}/teach": _COST,
        "POST /ide/exercises/generate": _COST,
        "PUT /ide/preferences": (
            "Préférences de l'IDE (mode du professeur, plafonds de coût) : réservées à "
            "January dans l'interface, un agent ne règle pas son propre budget."
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

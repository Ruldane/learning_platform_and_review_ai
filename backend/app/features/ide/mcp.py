"""Déclaration MCP de `ide` : exercices, séances, exécutions et notes. Claude lit, lance le code et
écrit des notes. Il n'écrit dans les fichiers de January que si elle a allumé l'interrupteur
(`mcp_can_write_files`, réglé dans l'interface seulement, `ide_write_file`, annulable) ; sinon une
correction est une proposition qu'elle accepte dans l'interface. Il ne déclenche pas le professeur
interne (coût d'API : Claude écrit lui-même ses notes et ses exercices)."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion, McpGraph

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
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/sessions",
            2,
            "ide_create_session",
            "Ouvre une séance de code, libre ou sur un exercice.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/runs",
            2,
            "ide_start_run",
            "Exécute ou vérifie le code d'une séance dans le bac à sable (sans réseau).",
            bucket="code_run",
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
            "stale_base, relis la séance. Jamais un fichier de test d'une séance sur exercice "
            "(`test_*.py`, `*_test.py`, `conftest.py`) : 403 mcp_ide_test_file, ce sont les "
            "siens. Annulable depuis « Accès MCP ».",
            body_fields=frozenset({"files", "base_hash"}),
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/files",
            2,
            "ide_create_project_file",
            "Ajoute un fichier au projet si l’écriture MCP a été autorisée. "
            "Prends la version `files_version` de `ide_get_session`.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "PATCH /ide/sessions/{session_id}/files",
            2,
            "ide_rename_project_file",
            "Renomme un fichier du projet si l’écriture MCP a été autorisée. "
            "Prends la version `files_version` de `ide_get_session`.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "DELETE /ide/sessions/{session_id}/files",
            3,
            "ide_delete_project_file",
            "Supprime un fichier du projet : demande à confirmer.",
            untrusted=("exercise_statement",),
        ),
        McpAction(
            "POST /ide/notes/{note_id}/accept",
            3,
            "ide_accept_note",
            "Applique la correction proposée dans la note. Demande à confirmer.",
        ),
        McpAction(
            "POST /ide/notes/{note_id}/reject",
            3,
            "ide_reject_note",
            "Refuse la correction proposée dans la note. Demande à confirmer.",
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/tabs",
            2,
            "ide_save_project_tabs",
            "Mémorise les onglets ouverts et le fichier sélectionné.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/terminal",
            2,
            "ide_open_terminal",
            "Ouvre le terminal dans le bac à sable sans réseau.",
            bucket="code_run",
        ),
        McpAction(
            "GET /ide/terminals/{run_id}",
            1,
            "ide_read_terminal",
            "Lit la sortie du terminal dans le bac à sable.",
            untrusted=("output",),
        ),
        McpAction(
            "POST /ide/terminals/{run_id}/input",
            2,
            "ide_write_terminal_input",
            "Envoie du texte au terminal du bac à sable sans réseau.",
            bucket="code_run",
        ),
        McpAction(
            "DELETE /ide/terminals/{run_id}",
            3,
            "ide_close_terminal",
            "Ferme le terminal. Demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/notebook",
            1,
            "ide_read_notebook",
            "Lit les cellules du notebook de la séance.",
            untrusted=("cells[].source", "cells[].output"),
        ),
        McpAction(
            "PUT /ide/sessions/{session_id}/notebook",
            2,
            "ide_save_notebook",
            "Enregistre les cellules du notebook si l’écriture MCP est autorisée.",
        ),
        McpAction(
            "POST /ide/sessions/{session_id}/notebook/run",
            2,
            "ide_run_notebook_cell",
            "Exécute une cellule du notebook dans le bac à sable.",
            bucket="code_run",
        ),
        McpAction(
            "GET /ide/notebook-runs/{run_id}",
            1,
            "ide_read_notebook_run",
            "Lit la sortie de l’exécution d’une cellule du notebook.",
            untrusted=("output",),
        ),
    ),
    graphs=(McpGraph("ide_teacher", follow_only=True), McpGraph("ide_exercise", follow_only=True)),
    play_actions=(
        McpAction(
            "POST /ide/sessions/{session_id}/teach", 2, "ide_teach_session", launches="ide_teacher"
        ),
        McpAction(
            "POST /ide/exercises/generate", 2, "ide_generate_exercise", launches="ide_exercise"
        ),
    ),
    excluded={
        "PUT /ide/preferences": McpExclusion.IDE_RIGHTS,
    },
)

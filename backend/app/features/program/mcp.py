"""Déclaration MCP de `program` : lire et retoucher le programme, le valider."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_FILE = (
    "Réponse en fichier (calendrier ou PDF), pas du JSON : le MCP lit le programme par "
    "`program_get_program`."
)

MCP = FeatureMcp(
    feature="program",
    actions=(
        McpAction("GET /programs", 1, "program_list_programs", "Les programmes d'apprentissage."),
        McpAction(
            "GET /programs/{program_id}",
            1,
            "program_get_program",
            "Un programme complet : modules, semaines, tâches.",
        ),
        McpAction(
            "PATCH /programs/{program_id}",
            2,
            "program_update_program",
            "Ajoute ou supprime des tâches, change la date de début d'un programme.",
        ),
        McpAction(
            "POST /programs/{program_id}/validate",
            3,
            "program_validate_program",
            "Valide le programme : compétences en cours, acquis en mémoire, leçons lancées. "
            "Décision de January et effets hors base : demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "PATCH /tasks/{task_id}",
            2,
            "program_update_task",
            "Déplace ou retouche une tâche du programme.",
        ),
        McpAction(
            "POST /programs/{program_id}/weeks",
            2,
            "program_add_week",
            "Écriture directe, aucun agent : ajoute une semaine (thème, objectif, livrable) à la "
            "fin du programme ; ses modules et ses tâches viennent ensuite.",
        ),
        McpAction(
            "PATCH /weeks/{week_id}",
            2,
            "program_update_week",
            "Écriture directe, aucun agent : retouche le thème, l'objectif ou le livrable d'une "
            "semaine.",
        ),
        McpAction(
            "POST /programs/{program_id}/modules",
            2,
            "program_add_module",
            "Écriture directe, aucun agent : ajoute un module (titre, compétences, prérequis) à "
            "une semaine du programme ; ses tâches se posent par `program_update_program`.",
        ),
        McpAction(
            "PATCH /modules/{module_id}",
            2,
            "program_update_module",
            "Écriture directe, aucun agent : retouche le titre, les compétences ou les prérequis "
            "d'un module.",
        ),
    ),
    graphs=(
        McpGraph(
            "program_builder",
            summary="Construit un programme depuis un objectif (`goal_id`) et ses parcours "
            "choisis (`proposal_ids`).",
        ),
    ),
    excluded={
        "GET /programs/{program_id}/export.ics": _FILE,
        "GET /programs/{program_id}/export.pdf": _FILE,
    },
)

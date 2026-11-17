"""Déclaration MCP de `learning` : objectifs, propositions du Conseil et états du tableau."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="learning",
    actions=(
        McpAction(
            "POST /goals",
            2,
            "learning_create_goal",
            "Crée un objectif d'apprentissage et lance le Conseil qui propose des parcours.",
            launches="learning_council",
        ),
        McpAction("GET /goals", 1, "learning_list_goals", "Les objectifs d'apprentissage."),
        McpAction("GET /goals/{goal_id}", 1, "learning_get_goal", "Un objectif et son état."),
        McpAction(
            "POST /goals/{goal_id}/council",
            2,
            "learning_retry_council",
            "Relance le Conseil d'un objectif dont la dernière session a échoué.",
            launches="learning_council",
        ),
        McpAction(
            "GET /goals/{goal_id}/proposals",
            1,
            "learning_list_proposals",
            "Les parcours proposés par le Conseil pour un objectif.",
        ),
        McpAction(
            "POST /proposals/{proposal_id}/choose",
            3,
            "learning_choose_proposal",
            "Choisit le parcours d'un objectif et lance la construction du programme : "
            "c'est une décision de January, demande à confirmer.",
        ),
        McpAction(
            "GET /goals/{goal_id}/boards",
            1,
            "learning_list_boards",
            "Les états du tableau du Conseil pour un objectif.",
        ),
        McpAction(
            "POST /boards/{board_id}/edits",
            2,
            "learning_edit_board",
            "Retouche l'état du tableau du Conseil (nouvelle version de l'état).",
        ),
    ),
    graphs=(
        McpGraph(
            "learning_council",
            summary="Le Conseil d'apprentissage sur un objectif (`goal_id`) : débat, "
            "cadrage et propositions de parcours.",
        ),
    ),
)

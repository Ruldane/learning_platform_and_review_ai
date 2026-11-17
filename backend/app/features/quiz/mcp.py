"""Déclaration MCP de `quiz` : quiz, tentatives et révision des fiches."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="quiz",
    actions=(
        McpAction(
            "POST /modules/{module_id}/quiz",
            2,
            "quiz_start_quiz",
            "Prépare le quiz d'un module (déjà prêt : le rend).",
            launches="quiz",
        ),
        McpAction(
            "GET /programs/{program_id}/quizzes",
            1,
            "quiz_list_quizzes",
            "Les quiz d'un programme.",
        ),
        McpAction("GET /quizzes/{quiz_id}", 1, "quiz_get_quiz", "Un quiz et ses questions."),
        McpAction(
            "POST /quizzes/{quiz_id}/attempts",
            2,
            "quiz_submit_attempt",
            "Envoie des réponses à un quiz et lance la notation.",
            launches="quiz",
        ),
        McpAction(
            "GET /quizzes/{quiz_id}/attempts/{attempt_id}",
            1,
            "quiz_get_attempt",
            "Le résultat d'une tentative.",
        ),
        McpAction(
            "GET /flashcards/due", 1, "quiz_list_due_cards", "La file de fiches à réviser du jour."
        ),
        McpAction(
            "POST /flashcards/{card_id}/review",
            2,
            "quiz_review_card",
            "Note une fiche due : sue ou non.",
        ),
    ),
    graphs=(
        McpGraph(
            "quiz",
            follow_only=True,
            summary="Écrit un quiz (`mode` generate, `quiz_id`) ou note une tentative "
            "(`mode` grade, `attempt_id`).",
        ),
    ),
)

"""Déclaration MCP de `quiz` : quiz, tentatives et révision des fiches."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_GESTURE = (
    "Geste de January : ses réponses, jamais faites à sa place (la notation d'un quiz et la "
    "révision d'une fiche valident ou rétrogradent ses acquis). Claude écrit le quiz et lit les "
    "résultats."
)

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
            "GET /quizzes/{quiz_id}/attempts/{attempt_id}",
            1,
            "quiz_get_attempt",
            "Le résultat d'une tentative.",
        ),
        McpAction(
            "GET /flashcards/due", 1, "quiz_list_due_cards", "La file de fiches à réviser du jour."
        ),
        McpAction(
            "POST /quizzes",
            2,
            "quiz_write_quiz",
            "Écriture directe, aucun agent : écrit le quiz d'un module (`module_id`, `title`, "
            "1 à 12 questions) ; il reste en préparation tant qu'il n'a pas 8 questions, 3 types "
            "différents et des énoncés d'au moins 10 caractères.",
        ),
        McpAction(
            "PATCH /quizzes/{quiz_id}",
            2,
            "quiz_update_quiz",
            "Écriture directe, aucun agent : change le titre d'un quiz prêt.",
        ),
        McpAction(
            "POST /quizzes/{quiz_id}/questions",
            2,
            "quiz_add_question",
            "Écriture directe, aucun agent : ajoute une question (QCM, courte, code ou "
            "explication) à un quiz prêt sans tentative.",
        ),
        McpAction(
            "PATCH /quizzes/{quiz_id}/questions/{question_id}",
            2,
            "quiz_update_question",
            "Écriture directe, aucun agent : retouche une question d'un quiz prêt sans tentative.",
        ),
    ),
    excluded={
        "POST /quizzes/{quiz_id}/attempts": _GESTURE,
        "POST /flashcards/{card_id}/review": _GESTURE,
    },
    graphs=(
        McpGraph(
            "quiz",
            follow_only=True,
            summary="Écrit un quiz (`mode` generate, `quiz_id`) ou note une tentative "
            "(`mode` grade, `attempt_id`).",
        ),
    ),
)

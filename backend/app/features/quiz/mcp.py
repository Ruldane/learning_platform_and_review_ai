"""MCP declaration for `quiz`: quizzes, attempts and card review."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_GESTURE = (
    "January's own action: her answers, never given on her behalf (grading a quiz and "
    "reviewing a card validate or downgrade her skills). Claude writes the quiz and reads "
    "the results."
)

MCP = FeatureMcp(
    feature="quiz",
    actions=(
        McpAction(
            "POST /modules/{module_id}/quiz",
            2,
            "quiz_start_quiz",
            "Prepares the quiz of a module (if already ready: returns it).",
            launches="quiz",
        ),
        McpAction(
            "GET /programs/{program_id}/quizzes",
            1,
            "quiz_list_quizzes",
            "The quizzes of a program.",
        ),
        McpAction("GET /quizzes/{quiz_id}", 1, "quiz_get_quiz", "A quiz and its questions."),
        McpAction(
            "GET /quizzes/{quiz_id}/attempts/{attempt_id}",
            1,
            "quiz_get_attempt",
            "The result of an attempt.",
        ),
        McpAction(
            "GET /flashcards/due", 1, "quiz_list_due_cards", "Today's queue of cards to review."
        ),
        McpAction(
            "POST /quizzes",
            2,
            "quiz_write_quiz",
            "Direct write, no agent: writes the quiz of a module (`module_id`, `title`, "
            "1 to 12 questions); it stays in preparation until it has 8 questions, 3 different "
            "types and prompts of at least 10 characters.",
        ),
        McpAction(
            "PATCH /quizzes/{quiz_id}",
            2,
            "quiz_update_quiz",
            "Direct write, no agent: changes the title of a ready quiz.",
        ),
        McpAction(
            "POST /quizzes/{quiz_id}/questions",
            2,
            "quiz_add_question",
            "Direct write, no agent: adds a question (multiple choice, short, code or "
            "explanation) to a ready quiz with no attempt.",
        ),
        McpAction(
            "PATCH /quizzes/{quiz_id}/questions/{question_id}",
            2,
            "quiz_update_question",
            "Direct write, no agent: edits a question of a ready quiz with no attempt.",
        ),
        McpAction(
            "POST /flashcards/{card_id}/review",
            3,
            "quiz_rate_flashcard",
            "Records the personal rating of the card. Needs confirmation.",
        ),
        McpAction(
            "POST /quizzes/{quiz_id}/attempts",
            3,
            "quiz_submit_attempt",
            "Records the quiz answers for grading. Needs confirmation.",
        ),
    ),
    graphs=(
        McpGraph(
            "quiz",
            follow_only=True,
            summary="Writes a quiz (`mode` generate, `quiz_id`) or grades an attempt "
            "(`mode` grade, `attempt_id`).",
        ),
    ),
)

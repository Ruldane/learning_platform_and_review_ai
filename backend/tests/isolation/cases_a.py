"""Cas d'isolation du flux A : pour chaque routeur de `FEATURE_ROUTERS`, le test qui prouve qu'un
autre compte ne lit ni n'écrit rien chez la première (404 sur ses objets, listes vides, ses propres
valeurs pour les réglages). Les routeurs `costs` et `account` ont leurs cas dans `cases_b.py`
(flux B) ; `health` est exempté (`guard_support.EXEMPT`). Ce module n'importe rien : seul le
dictionnaire compte (routeur → identifiant de test)."""

CASES: dict[str, str] = {
    # Cas existants, référencés.
    "app.features.settings.keys_router": (
        "tests/features/settings/test_keys_router.py::test_brave_key_isolated_between_users"
    ),
    "app.features.sessions.router": (
        "tests/features/sessions/test_router.py::test_other_user_cannot_read_or_drive_session"
    ),
    "app.features.sessions.play_router": (
        "tests/isolation/test_played_sessions.py::test_foreign_session_is_invisible"
    ),
    "app.features.memory.router.items": (
        "tests/features/memory/test_items_router.py::test_items_isolated_between_users"
    ),
    "app.features.research.router": (
        "tests/features/research/test_router.py"
        "::test_sources_route_lists_session_sources_and_is_isolated"
    ),
    "app.features.learning.router": (
        "tests/features/learning/test_goals_router.py::test_goals_isolated_between_users"
    ),
    "app.features.program.router": (
        "tests/features/program/test_router.py::test_programs_isolated_between_users"
    ),
    "app.features.book.router": (
        "tests/features/book/test_book_routes.py::test_book_routes_are_isolated"
    ),
    "app.features.lessons.router": (
        "tests/features/lessons/test_router.py::test_lesson_routes_and_isolation"
    ),
    "app.features.quiz.router": (
        "tests/features/quiz/test_router.py::test_quiz_routes_isolate_users"
    ),
    "app.features.study.router_training": (
        "tests/features/study/test_router.py::test_study_routes_isolate_users"
    ),
    "app.features.brain.router_chat": (
        "tests/isolation/test_brain_conversation.py::test_brain_thread_is_private_to_each_account"
    ),
    "app.features.conversations.router": (
        "tests/isolation/test_conversations.py"
        "::test_cannot_read_or_add_to_another_accounts_conversation"
    ),
    "app.features.conversations.feynman_router": (
        "tests/isolation/test_conversations.py::test_feynman_context_and_report_are_private"
    ),
    "app.features.replan.router": (
        "tests/features/replan/test_router.py::test_replan_routes_isolate_users"
    ),
    "app.features.skills.router": (
        "tests/features/skills/test_router.py::test_skills_routes_isolate_users"
    ),
    "app.features.contributions.router": (
        "tests/features/contributions/test_routes.py"
        "::test_another_account_cannot_open_or_publish_a_contribution"
    ),
    "app.features.capture.router": (
        "tests/features/capture/test_router.py::test_capture_and_journal_isolate_users"
    ),
    "app.features.postings.router": (
        "tests/features/postings/test_router.py::test_other_user_posting_is_404"
    ),
    "app.features.applications.router": (
        "tests/features/applications/test_update.py::test_other_user_sees_nothing"
    ),
    "app.features.applications.router_kit": (
        "tests/features/applications/test_kit_access.py::test_other_user_kit_404"
    ),
    "app.features.applications.router_interviews": (
        "tests/features/applications/test_interviews_access.py::test_other_user_gets_404"
    ),
    "app.features.applications.router_system_design": (
        "tests/isolation/test_system_design.py::test_system_design_board_and_review_are_private"
    ),
    "app.features.applications.router_committee": (
        "tests/features/applications/test_committee_access.py::test_other_user_gets_404"
    ),
    "app.features.radar.router": "tests/features/radar/test_runs.py::test_other_user_run_404",
    "app.features.brief.router": (
        "tests/features/brief/test_ensure.py::test_other_user_brief_isolated"
    ),
    "app.features.projects.router": (
        "tests/features/projects/test_isolation.py"
        "::test_another_user_cannot_reach_any_route_of_my_project"
    ),
    "app.features.portfolio.router": (
        "tests/isolation/test_portfolio.py::test_other_account_cannot_read_or_publish_a_private_portfolio"
    ),
    # Cas écrits par 9.A4 (routeurs qui n'en avaient pas au niveau des routes).
    "app.features.auth.router": (
        "tests/isolation/test_cross_user_auth.py::test_two_accounts_have_their_own_identity"
    ),
    "app.features.settings.router": (
        "tests/isolation/test_cross_user_settings.py::test_settings_are_each_accounts_own"
    ),
    "app.features.gap.router": (
        "tests/isolation/test_cross_user_gap.py::test_gap_of_another_account_is_invisible"
    ),
    "app.features.cv.router.profile": (
        "tests/isolation/test_cross_user_cv.py::test_cv_of_another_account_is_invisible"
    ),
    "app.features.applications.router_reminders": (
        "tests/isolation/test_cross_user_reminders.py::test_reminders_of_another_account_are_invisible"
    ),
    "app.features.activity.router": (
        "tests/isolation/test_cross_user_activity.py::test_activity_of_another_account_is_invisible"
    ),
    "app.features.ide.router_project": (
        "tests/isolation/test_ide_project_api.py"
        "::test_foreign_project_file_and_tab_operations_are_refused"
    ),
    "app.features.mcp.router": "tests/mcp/test_isolation.py::test_mcp_user_isolation",
    "app.features.mcp.relay_router": (
        "tests/isolation/test_mcp_relay_pairing.py"
        "::test_relay_pairing_belongs_to_the_account_that_created_the_code"
    ),
    "app.features.reading_stack.router": (
        "tests/isolation/test_reading_stack.py::test_reading_sources_items_and_actions_are_private"
    ),
    "app.features.reading_stack.router_actions": (
        "tests/isolation/test_reading_stack.py::test_reading_sources_items_and_actions_are_private"
    ),
}

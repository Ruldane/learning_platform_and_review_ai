from fastapi import APIRouter

from app.features.account.mcp import MCP as account_mcp
from app.features.account.router import router as account_router
from app.features.activity.mcp import MCP as activity_mcp
from app.features.activity.router import router as activity_router
from app.features.applications.mcp import MCP as applications_mcp
from app.features.applications.router import router as applications_router
from app.features.applications.router_committee import router as committee_router
from app.features.applications.router_interviews import router as interviews_router
from app.features.applications.router_kit import router as kit_router
from app.features.applications.router_reminders import router as reminders_router
from app.features.applications.router_system_design import router as design_interviews_router
from app.features.auth.mcp import MCP as auth_mcp
from app.features.auth.router import router as auth_router
from app.features.book.mcp import MCP as book_mcp
from app.features.book.router import router as book_router
from app.features.boss.mcp import MCP as boss_mcp
from app.features.boss.router import router as boss_router
from app.features.brain.mcp import MCP as brain_mcp
from app.features.brain.router import router as brain_router
from app.features.brief.mcp import MCP as brief_mcp
from app.features.brief.router import router as brief_router
from app.features.calendar.mcp import MCP as calendar_mcp
from app.features.calendar.router import router as calendar_router
from app.features.capture.mcp import MCP as capture_mcp
from app.features.capture.router import router as capture_router
from app.features.code_trial.mcp import MCP as code_trial_mcp
from app.features.code_trial.router import router as code_trial_router
from app.features.compatible_offers.mcp import MCP as compatible_offers_mcp
from app.features.compatible_offers.router import router as compatible_offers_router
from app.features.contributions.mcp import MCP as contributions_mcp
from app.features.contributions.router import router as contributions_router
from app.features.conversations.feynman_router import router as feynman_router
from app.features.conversations.mcp import MCP as conversations_mcp
from app.features.conversations.router import router as conversations_router
from app.features.costs.mcp import MCP as costs_mcp
from app.features.costs.router import router as costs_router
from app.features.cv.mcp import MCP as cv_mcp
from app.features.cv.router import router as cv_router
from app.features.expert_debates.mcp import MCP as expert_debates_mcp
from app.features.expert_debates.router import router as expert_debates_router
from app.features.future_self.mcp import MCP as future_self_mcp
from app.features.future_self.router import router as future_self_router
from app.features.galaxy.mcp import MCP as galaxy_mcp
from app.features.galaxy.router import router as galaxy_router
from app.features.gap.mcp import MCP as gap_mcp
from app.features.gap.router import router as gap_router
from app.features.ghost.mcp import MCP as ghost_mcp
from app.features.ghost.router import router as ghost_router
from app.features.health.mcp import MCP as health_mcp
from app.features.health.router import router as health_router
from app.features.ide.mcp import MCP as ide_mcp
from app.features.ide.router import router as ide_router
from app.features.learning.mcp import MCP as learning_mcp
from app.features.learning.router import router as learning_router
from app.features.lesson_hunt.mcp import MCP as lesson_hunt_mcp
from app.features.lesson_hunt.router import router as lesson_hunt_router
from app.features.lesson_updates.mcp import MCP as lesson_updates_mcp
from app.features.lesson_updates.router import router as lesson_updates_router
from app.features.lessons.mcp import MCP as lessons_mcp
from app.features.lessons.router import router as lessons_router
from app.features.linkedin_drafts.mcp import MCP as linkedin_drafts_mcp
from app.features.linkedin_drafts.router import router as linkedin_drafts_router
from app.features.mcp.mcp import MCP as mcp_mcp
from app.features.mcp.relay_router import router as mcp_relay_router
from app.features.mcp.router import router as mcp_router
from app.features.memory.mcp import MCP as memory_mcp
from app.features.memory.router import router as memory_router
from app.features.message_review.mcp import MCP as message_review_mcp
from app.features.message_review.router import router as message_review_router
from app.features.oncall.mcp import MCP as oncall_mcp
from app.features.oncall.router import router as oncall_router
from app.features.paper_lab.mcp import MCP as paper_lab_mcp
from app.features.paper_lab.router import router as paper_lab_router
from app.features.podcast.mcp import MCP as podcast_mcp
from app.features.podcast.router import router as podcast_router
from app.features.postings.mcp import MCP as postings_mcp
from app.features.postings.router import router as postings_router
from app.features.program.mcp import MCP as program_mcp
from app.features.program.router import router as program_router
from app.features.projects.mcp import MCP as projects_mcp
from app.features.projects.router import router as projects_router
from app.features.quiz.mcp import MCP as quiz_mcp
from app.features.quiz.router import router as quiz_router
from app.features.radar.mcp import MCP as radar_mcp
from app.features.radar.router import router as radar_router
from app.features.reading_stack.mcp import MCP as reading_stack_mcp
from app.features.reading_stack.router import router as reading_stack_router
from app.features.reading_stack.router_actions import router as reading_actions_router
from app.features.replan.mcp import MCP as replan_mcp
from app.features.replan.router import router as replan_router
from app.features.research.mcp import MCP as research_mcp
from app.features.research.router import router as research_router
from app.features.sessions.mcp import MCP as sessions_mcp
from app.features.sessions.play_router import router as sessions_play_router
from app.features.sessions.router import router as sessions_router
from app.features.settings.keys_router import router as keys_router
from app.features.settings.mcp import MCP as settings_mcp
from app.features.settings.router import router as settings_router
from app.features.skill_market.mcp import MCP as skill_market_mcp
from app.features.skill_market.router import router as skill_market_router
from app.features.skills.mcp import MCP as skills_mcp
from app.features.skills.router import router as skills_router
from app.features.study.mcp import MCP as study_mcp
from app.features.study.router import router as study_router
from app.features.surprise_interview.mcp import MCP as surprise_interview_mcp
from app.features.surprise_interview.router import router as surprise_interview_router
from app.features.voice.mcp import MCP as voice_mcp
from app.features.voice.router import router as voice_router
from app.mcp.base import FeatureMcp

# Chaque feature ajoute ici son routeur ; `create_app` les monte sous `/api/v1`.
FEATURE_ROUTERS: list[APIRouter] = [
    auth_router,
    settings_router,
    calendar_router,
    keys_router,
    health_router,
    sessions_play_router,  # avant `sessions_router` : `/sessions/play` avant `/{session_id}`
    sessions_router,
    memory_router,
    brain_router,
    oncall_router,
    research_router,
    learning_router,
    program_router,
    book_router,
    boss_router,
    lesson_hunt_router,
    lesson_updates_router,
    lessons_router,
    linkedin_drafts_router,
    conversations_router,
    feynman_router,
    expert_debates_router,
    quiz_router,
    message_review_router,
    ghost_router,
    study_router,
    surprise_interview_router,
    replan_router,
    skill_market_router,
    skills_router,
    galaxy_router,
    contributions_router,
    capture_router,
    postings_router,
    gap_router,
    cv_router,
    applications_router,
    kit_router,
    interviews_router,
    design_interviews_router,
    committee_router,
    reminders_router,
    radar_router,
    future_self_router,
    reading_stack_router,
    reading_actions_router,
    brief_router,
    paper_lab_router,
    podcast_router,
    voice_router,
    activity_router,
    projects_router,
    account_router,
    costs_router,
    ide_router,
    code_trial_router,
    compatible_offers_router,
    mcp_router,
    mcp_relay_router,
]

# Chaque feature déclare ici ses outils MCP (`features/<f>/mcp.py`, `MCP: FeatureMcp`), une
# ligne par feature : liste blanche, aucune route n'est exposée d'elle-même (phase 10, P11).
MCP_FEATURES: list[FeatureMcp] = [
    account_mcp,
    activity_mcp,
    applications_mcp,
    auth_mcp,
    book_mcp,
    boss_mcp,
    brain_mcp,
    brief_mcp,
    calendar_mcp,
    capture_mcp,
    code_trial_mcp,
    compatible_offers_mcp,
    contributions_mcp,
    conversations_mcp,
    costs_mcp,
    cv_mcp,
    expert_debates_mcp,
    future_self_mcp,
    galaxy_mcp,
    gap_mcp,
    ghost_mcp,
    health_mcp,
    ide_mcp,
    learning_mcp,
    lesson_hunt_mcp,
    lesson_updates_mcp,
    lessons_mcp,
    linkedin_drafts_mcp,
    mcp_mcp,
    memory_mcp,
    message_review_mcp,
    oncall_mcp,
    paper_lab_mcp,
    podcast_mcp,
    postings_mcp,
    program_mcp,
    projects_mcp,
    quiz_mcp,
    radar_mcp,
    reading_stack_mcp,
    replan_mcp,
    research_mcp,
    sessions_mcp,
    settings_mcp,
    skill_market_mcp,
    skills_mcp,
    study_mcp,
    surprise_interview_mcp,
    voice_mcp,
]

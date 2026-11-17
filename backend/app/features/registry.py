from fastapi import APIRouter

from app.features.account.router import router as account_router
from app.features.activity.router import router as activity_router
from app.features.applications.router import router as applications_router
from app.features.applications.router_committee import router as committee_router
from app.features.applications.router_interviews import router as interviews_router
from app.features.applications.router_kit import router as kit_router
from app.features.applications.router_reminders import router as reminders_router
from app.features.auth.router import router as auth_router
from app.features.brief.router import router as brief_router
from app.features.capture.router import router as capture_router
from app.features.costs.router import router as costs_router
from app.features.cv.router import router as cv_router
from app.features.gap.router import router as gap_router
from app.features.health.router import router as health_router
from app.features.ide.router import router as ide_router
from app.features.learning.router import router as learning_router
from app.features.lessons.router import router as lessons_router
from app.features.mcp.router import router as mcp_router
from app.features.memory.router import router as memory_router
from app.features.postings.router import router as postings_router
from app.features.program.router import router as program_router
from app.features.projects.router import router as projects_router
from app.features.quiz.router import router as quiz_router
from app.features.radar.router import router as radar_router
from app.features.replan.router import router as replan_router
from app.features.research.router import router as research_router
from app.features.sessions.router import router as sessions_router
from app.features.settings.keys_router import router as keys_router
from app.features.settings.router import router as settings_router
from app.features.skills.router import router as skills_router
from app.features.study.router import router as study_router
from app.mcp.base import FeatureMcp

# Chaque feature ajoute ici son routeur ; `create_app` les monte sous `/api/v1`.
FEATURE_ROUTERS: list[APIRouter] = [
    auth_router,
    settings_router,
    keys_router,
    health_router,
    sessions_router,
    memory_router,
    research_router,
    learning_router,
    program_router,
    lessons_router,
    quiz_router,
    study_router,
    replan_router,
    skills_router,
    capture_router,
    postings_router,
    gap_router,
    cv_router,
    applications_router,
    kit_router,
    interviews_router,
    committee_router,
    reminders_router,
    radar_router,
    brief_router,
    activity_router,
    projects_router,
    account_router,
    costs_router,
    ide_router,
    mcp_router,
]

# Chaque feature déclare ici ses outils MCP (`features/<f>/mcp.py`, `MCP: FeatureMcp`), une
# ligne par feature : liste blanche, aucune route n'est exposée d'elle-même (phase 10, P11).
# Remplie par 10.D1.
MCP_FEATURES: list[FeatureMcp] = []

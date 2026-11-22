"""Routes et outils MCP des nouveaux parcours Tremplin."""

from app.features.blind_assessment.mcp import MCP as blind_assessment_mcp
from app.features.blind_assessment.router import router as blind_assessment_router
from app.features.contradictory_watch.mcp import MCP as contradictory_watch_mcp
from app.features.contradictory_watch.router import router as contradictory_watch_router
from app.features.data_investigation.mcp import MCP as data_investigation_mcp
from app.features.data_investigation.router import router as data_investigation_router
from app.features.dated_commitments.mcp import MCP as dated_commitments_mcp
from app.features.dated_commitments.router import router as dated_commitments_router
from app.features.decision_lab.mcp import MCP as decision_lab_mcp
from app.features.decision_lab.router import router as decision_lab_router
from app.features.error_atlas.mcp import MCP as error_atlas_mcp
from app.features.error_atlas.router import router as error_atlas_router
from app.features.grade_appeals.mcp import MCP as grade_appeals_mcp
from app.features.grade_appeals.router import router as grade_appeals_router
from app.features.incident_replay.mcp import MCP as incident_replay_mcp
from app.features.incident_replay.router import router as incident_replay_router
from app.features.interprogram_planning.mcp import MCP as interprogram_planning_mcp
from app.features.interprogram_planning.router import router as interprogram_planning_router
from app.features.lesson_variants.mcp import MCP as lesson_variants_mcp
from app.features.lesson_variants.router import router as lesson_variants_router
from app.features.meeting_modules.mcp import MCP as meeting_modules_mcp
from app.features.meeting_modules.router import router as meeting_modules_router
from app.features.mentor_reviews.mcp import MCP as mentor_reviews_mcp
from app.features.mentor_reviews.router import router as mentor_reviews_router
from app.features.missions.mcp import MCP as missions_mcp
from app.features.missions.router import router as missions_router
from app.features.offer_comparison.mcp import MCP as offer_comparison_mcp
from app.features.offer_comparison.router import router as offer_comparison_router
from app.features.project_handoffs.mcp import MCP as project_handoffs_mcp
from app.features.project_handoffs.router import router as project_handoffs_router
from app.features.proof_packets.mcp import MCP as proof_packets_mcp
from app.features.proof_packets.router import router as proof_packets_router
from app.features.recruitment_process.mcp import MCP as recruitment_process_mcp
from app.features.recruitment_process.router import router as recruitment_process_router
from app.features.routines.mcp import MCP as routines_mcp
from app.features.routines.router import router as routines_router
from app.features.skill_transfer.mcp import MCP as skill_transfer_mcp
from app.features.skill_transfer.router import router as skill_transfer_router
from app.features.study_return.mcp import MCP as study_return_mcp
from app.features.study_return.router import router as study_return_router

WORKFLOWS = (
    (routines_router, routines_mcp),
    (missions_router, missions_mcp),
    (decision_lab_router, decision_lab_mcp),
    (skill_transfer_router, skill_transfer_mcp),
    (contradictory_watch_router, contradictory_watch_mcp),
    (error_atlas_router, error_atlas_mcp),
    (proof_packets_router, proof_packets_mcp),
    (blind_assessment_router, blind_assessment_mcp),
    (incident_replay_router, incident_replay_mcp),
    (interprogram_planning_router, interprogram_planning_mcp),
    (mentor_reviews_router, mentor_reviews_mcp),
    (data_investigation_router, data_investigation_mcp),
    (dated_commitments_router, dated_commitments_mcp),
    (meeting_modules_router, meeting_modules_mcp),
    (study_return_router, study_return_mcp),
    (recruitment_process_router, recruitment_process_mcp),
    (grade_appeals_router, grade_appeals_mcp),
    (lesson_variants_router, lesson_variants_mcp),
    (project_handoffs_router, project_handoffs_mcp),
    (offer_comparison_router, offer_comparison_mcp),
)
WORKFLOW_ROUTERS = tuple(router for router, _ in WORKFLOWS)
WORKFLOW_MCP = tuple(mcp for _, mcp in WORKFLOWS)

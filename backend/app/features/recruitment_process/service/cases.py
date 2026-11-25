"""An analyzed job posting, attested skills and three comparable steps."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.recruitment_process_port import RecruitmentCriterion
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.features.postings.service.queries import list_postings, read_posting
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import get_project, list_projects
from app.features.recruitment_process.repository import RecruitmentCases
from app.features.recruitment_process.schemas import (
    RecruitmentChoice,
    RecruitmentCreate,
    RecruitmentMissingProof,
    RecruitmentOptions,
    RecruitmentOut,
    RecruitmentStep,
)
from app.features.recruitment_process.service.steps import view

_REVIEWED = {"validated", "to_redo"}
_RUBRIC = (
    RecruitmentCriterion(
        label="Fit with the job posting",
        instructions="The answer addresses the posting's expectations and justifies priorities.",
    ),
    RecruitmentCriterion(
        label="Approach",
        instructions="The steps, checks and limits of the approach are explicit.",
    ),
    RecruitmentCriterion(
        label="Verifiable evidence",
        instructions="Claims are backed by specific facts, measurements or tests.",
    ),
)


def _prompts(requirement: str) -> list[RecruitmentStep]:
    return [
        RecruitmentStep(
            kind="project",
            prompt=(
                f"Show how your project meets this expectation of the job posting. {requirement}\n"
                "Explain your role, the decisions made and a verifiable result. "
                "State what still remains to be demonstrated."
            ),
        ),
        RecruitmentStep(
            kind="exercise",
            prompt=(
                "Scenario. A first solution partially meets this expectation. "
                f"{requirement}\n"
                "The deadline is short and the data is incomplete. Describe the first step "
                "you would take, one risk, and the check that would make you change your mind."
            ),
        ),
        RecruitmentStep(
            kind="interview",
            prompt=(
                "The recruiter asks what your experience demonstrates for this expectation. "
                f"{requirement}\n"
                "Give an example with context, action and result. If the recruiter questions "
                "your result, what evidence can you present and which limit would you admit?"
            ),
        ),
    ]


async def options(rt: ProjectsRuntime, db: AsyncSession, user_id: str) -> RecruitmentOptions:
    return RecruitmentOptions(
        postings=[
            RecruitmentChoice(
                id=item.id,
                title=" · ".join(
                    filter(None, (item.title or "Analyzed job posting", item.company))
                ),
            )
            for item in await list_postings(db, user_id)
            if item.status == "ready"
        ],
        projects=[
            RecruitmentChoice(id=item.id, title=item.title)
            for item in await list_projects(rt, db, user_id, None)
            if item.status in _REVIEWED
        ],
    )


async def _project(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, project_id: str | None
) -> dict[str, object] | None:
    if project_id is None:
        return None
    found = await get_project(rt, db, user_id, project_id)
    if found.status not in _REVIEWED or not found.submissions or found.evaluation is None:
        raise AppError(
            "recruitment_project_not_reviewed", "Choose a project that was already reviewed.", 409
        )
    return {
        "id": found.id,
        "title": found.title,
        "objective": found.brief.objective[:1500] if found.brief else None,
        "result": found.submissions[0].description,
        "critique": found.evaluation.feedback[:1500],
    }


async def create(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, body: RecruitmentCreate
) -> RecruitmentOut:
    posting = await read_posting(db, user_id, str(body.posting_id))
    analysis = posting.analysis
    if posting.status != "ready" or analysis is None:
        raise AppError(
            "recruitment_offer_pending", "Choose a job posting whose analysis is ready.", 409
        )
    cases = RecruitmentCases(db, user_id)
    demonstrated = await cases.demonstrated_skills()
    required = [entry for entry in analysis.requirements if entry.required]
    missing = []
    for entry in required:
        gaps = [skill for skill in entry.skills if normalize_skill_name(skill) not in demonstrated]
        if not entry.skills or gaps:
            missing.append(RecruitmentMissingProof(requirement=entry.text, skills=gaps))
    requirements = [entry.text for entry in required or analysis.requirements]
    anchor = requirements[0] if requirements else analysis.title
    project_id = str(body.project_id) if body.project_id else None
    row = await cases.add(
        posting_id=posting.id,
        offer={"title": analysis.title, "company": analysis.company, "requirements": requirements},
        project=await _project(rt, db, user_id, project_id),
        rubric=[criterion.model_dump() for criterion in _RUBRIC],
        missing_proofs=[entry.model_dump() for entry in missing],
        steps=[step.model_dump() for step in _prompts(anchor)],
    )
    return await view(db, row)

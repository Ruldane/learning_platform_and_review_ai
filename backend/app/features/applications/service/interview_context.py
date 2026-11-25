"""What the `interview` flow reads (`InterviewContext`, D146): the interview's setting, then,
depending on its origin, the record (exact title, frozen copy of the posting text, CV version
sent, linked posting), the posting alone for a free interview, or the title alone. The company
dossier (`companies.dossier`) is only used if it is under 30 days old; the gaps are the
posting's needs that no known skill covers; the validated master profile is required.

Read-only, on behalf of the user. Nothing is logged here."""

from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.interview_schema import InterviewContext
from app.agents.tools.kit_schema import CompanyDossier
from app.agents.tools.negotiation import SalarySample
from app.agents.tools.posting_schema import PostingAnalysis
from app.db.models.applications import Application, Interview
from app.db.models.postings import JobPosting
from app.features.applications.repository import ApplicationRepository, CompanyRepository
from app.features.applications.service.kit_language import posting_analysis
from app.features.applications.service.kit_store import (
    company_name_key,
    dossier_of,
    profile_required,
)
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.versions import (
    ready_versions_by_posting,
    validated_profile,
    version_content,
)
from app.features.postings.service.queries import postings_by_ids

DEFAULT_ROLE = "Role"


@dataclass(frozen=True)
class Source:
    """Where the interview comes from: the title, the company, the posting (text and analysis)."""

    role: str
    company: str | None
    text: str | None
    analysis: PostingAnalysis | None
    posting: JobPosting | None
    cv_version_id: str | None


def _analysis_of(posting: JobPosting) -> PostingAnalysis | None:
    if not posting.analysis:
        return None
    try:
        return PostingAnalysis.model_validate(posting.analysis)
    except ValidationError:
        return None


def _from_application(application: Application, posting: JobPosting | None, role: str) -> Source:
    text = (application.posting_text or (posting.text if posting else "") or "").strip()
    analysis = (
        posting_analysis(posting.analysis if posting else None, application, text) if text else None
    )
    return Source(
        role, application.company, text or None, analysis, posting, application.cv_version_id
    )


def _from_posting(posting: JobPosting, role: str) -> Source:
    analysis = _analysis_of(posting)
    company = posting.company or (analysis.company if analysis else None)
    return Source(role, company, posting.text.strip() or None, analysis, posting, None)


async def load_source(db: AsyncSession, user_id: str, row: Interview) -> Source:
    """The record (if it still exists: an interview outlives it), else the posting or the title."""
    application = None
    if row.application_id is not None:
        application = await ApplicationRepository(db, user_id).get(row.application_id)
    posting_id = row.posting_id or (application.posting_id if application else None)
    posting = None
    if posting_id is not None:
        posting = (await postings_by_ids(db, user_id, [posting_id])).get(posting_id)
    role = row.role or (application.title if application else None) or DEFAULT_ROLE
    if application is not None:
        return _from_application(application, posting, role)
    if posting is not None:
        return _from_posting(posting, role)
    return Source(role, None, None, None, None, None)


def gaps_of(posting: JobPosting | None) -> list[str]:
    """The posting's needs that no known skill covers (stored gap analysis)."""
    matches = (posting.gap or {}).get("matches", []) if posting is not None else []
    return [str(match["need"]) for match in matches if match.get("known") is None]


async def _dossier(
    rt: ApplicationsRuntime, db: AsyncSession, user_id: str, company: str | None
) -> CompanyDossier | None:
    if not company:
        return None
    row = await CompanyRepository(db, user_id).by_key(company_name_key(company))
    return dossier_of(row, rt.now())[0]


async def build_context(rt: ApplicationsRuntime, user_id: str, row: Interview) -> InterviewContext:
    """The context of interview `row`; 409 `profile_required` without a validated profile."""
    async with rt.session_factory() as db:
        profile = await validated_profile(db, user_id)
        if profile is None:
            raise profile_required()
        source = await load_source(db, user_id, row)
        version_id = source.cv_version_id
        if version_id is None and source.posting is not None:
            ready = (await ready_versions_by_posting(db, user_id)).get(source.posting.id)
            version_id = ready[0] if ready else None
        cv = await version_content(db, user_id, version_id) if version_id else None
        dossier = await _dossier(rt, db, user_id, source.company)
    return InterviewContext(
        mode=row.mode,  # type: ignore[arg-type]  # colonnes texte, valeurs d'`InterviewMode`
        duration_min=row.duration_min,  # type: ignore[arg-type]
        language=row.language,  # type: ignore[arg-type]
        role=source.role,
        posting_text=source.text,
        analysis=source.analysis,
        dossier=dossier,
        cv_content=cv,
        gaps=gaps_of(source.posting),
        profile=profile,
        salary=SalarySample.model_validate(row.salary) if row.salary is not None else None,
        surprise=row.surprise_invitation_id is not None,
    )

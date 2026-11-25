"""Hiring committee port (`CommitteeStore`, D147) on the `applications` feature:
implementation wired by `bootstrap_agents.agent_ports(..., committee=...)`. Each call opens its
own short database session.

- `context`: read-only. The run (404 `committee_not_found` if it is not the user's), the CV of
  the version (text without name or contact details), the posting (text and analysis, otherwise
  a minimal analysis: no invented requirement), the exact company and title (from the posting's
  record if it exists), the dossier under 30 days old (`kit_store.dossier_of`, the rule of the
  kit and of the interview) and the size it gives, the posting terms seen in the CV
  (`ats_terms_of`) and the validated master profile (409 `profile_required`).
- `save_result`: **idempotent per session**, under the committee lock: a run that is no longer
  `running` (replay after a stop, SPEC 9.4) is never rewritten. Stores the votes, the verdict,
  the objections and the changes, sets the run to `done` and, if the posting has a record, adds
  the `committee` event to its timeline, in the same transaction.

Logs: ids, statuses and numbers only (17.2)."""

import logging
from collections import Counter

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.committee_schema import (
    CommitteeContext,
    PersonaVote,
    Synthesis,
    ats_terms_of,
    cv_plain_text,
)
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.applications import Application, CommitteeRun
from app.db.models.postings import JobPosting
from app.features.applications.repository import (
    ApplicationRepository,
    CompanyRepository,
    EventRepository,
)
from app.features.applications.service.committee import committee_lock, committee_row
from app.features.applications.service.kit_language import posting_analysis, text_language
from app.features.applications.service.kit_store import (
    company_name_key,
    dossier_of,
    profile_required,
)
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.versions import validated_profile, version_content
from app.features.postings.service.queries import postings_by_ids

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "Role"


def _analysis(posting: JobPosting, application: Application | None) -> PostingAnalysis:
    """The stored analysis of the posting; otherwise a minimal analysis (title, company,
    language). With a record, it is the kit's (`kit_language.posting_analysis`, a single rule)."""
    if application is not None:
        return posting_analysis(posting.analysis, application, posting.text)
    if posting.analysis:
        try:
            return PostingAnalysis.model_validate(posting.analysis)
        except ValidationError:
            pass  # an unreadable analysis: the posting text remains the source
    return PostingAnalysis(
        is_job_posting=True,
        title=(posting.title or DEFAULT_TITLE).ljust(2, "."),
        company=posting.company,
        level="unknown",
        language=text_language(posting.text),
    )


def timeline_text(synthesis: Synthesis, votes: list[PersonaVote]) -> str:
    counts = Counter(vote.vote for vote in votes)
    return (
        f"The simulated hiring committee voted {synthesis.verdict} "
        f"({counts['yes']} yes, {counts['no']} no, {counts['maybe']} maybe) "
        f"and proposed {len(synthesis.changes)} changes."
    )


class AgentCommitteeStore:
    def __init__(self, runtime: ApplicationsRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, run_id: str) -> CommitteeContext:
        rt = self._rt
        async with rt.session_factory() as db:
            row = await committee_row(db, user_id, run_id)
            profile = await validated_profile(db, user_id)
            if profile is None:
                raise profile_required()
            cv = await version_content(db, user_id, row.cv_version_id)
            posting = (await postings_by_ids(db, user_id, [row.posting_id])).get(row.posting_id)
            if cv is None or posting is None:
                raise AppError(
                    "version_not_ready",
                    "The CV or the posting for this committee run is no longer available.",
                    409,
                )
            application = await ApplicationRepository(db, user_id).by_posting(row.posting_id)
            analysis = _analysis(posting, application)
            company = (application.company if application else posting.company) or analysis.company
            record = None
            if company:
                record = await CompanyRepository(db, user_id).by_key(company_name_key(company))
        dossier, _ = dossier_of(record, rt.now())
        cv_text = cv_plain_text(cv)
        return CommitteeContext(
            cv_text=cv_text,
            posting_text=posting.text,
            analysis=analysis,
            dossier=dossier,
            size=dossier.size if dossier else "unknown",
            ats_terms=ats_terms_of(analysis, cv_text),
            profile=profile,
            company=company,
            title=(application.title if application else posting.title) or analysis.title,
        )

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None:
        rt = self._rt
        async with committee_lock(rt, user_id), rt.session_factory() as db:
            row = await committee_row(db, user_id, run_id)
            if row.status != "running":
                return  # replay: the outcome of the session is already stored
            row.votes = [vote.model_dump(mode="json") for vote in votes]
            row.verdict = synthesis.verdict
            row.objections = [o.model_dump(mode="json") for o in synthesis.objections]
            row.changes = [c.model_dump(mode="json") for c in synthesis.changes]
            row.status = "done"
            await self._timeline(db, user_id, row, votes, synthesis)
            await db.commit()
        logger.info(
            "Committee stored: user %s, run %s, session %s, verdict %s",
            user_id,
            run_id,
            session_id,
            synthesis.verdict,
        )

    async def _timeline(
        self,
        db: AsyncSession,
        user_id: str,
        row: CommitteeRun,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None:
        """The `committee` event of the posting's record, if it exists (same transaction)."""
        application = await ApplicationRepository(db, user_id).by_posting(row.posting_id)
        if application is None:
            return
        row.application_id = application.id
        await EventRepository(db, user_id).add(
            application_id=application.id,
            kind="committee",
            at=self._rt.now(),
            text=timeline_text(synthesis, votes),
            ref_id=row.id,
        )

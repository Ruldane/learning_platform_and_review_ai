"""Port du comité de recrutement (`CommitteeStore`, D147) sur la feature `applications` :
implémentation branchée par `bootstrap_agents.agent_ports(..., committee=...)`. Chaque appel ouvre
sa propre session de base, courte.

- `context` : lecture seule. L'exécution (404 `committee_not_found` si elle n'est pas à
  l'utilisatrice), le CV de la version (texte sans nom ni coordonnées), l'offre (texte et analyse,
  sinon une analyse minimale : aucune exigence inventée), l'entreprise et l'intitulé exacts (de la
  fiche de l'offre si elle existe), le dossier de moins de 30 jours (`kit_store.dossier_of`, la
  règle du kit et de l'entretien) et la taille qu'il donne, les termes de l'offre vus dans le CV
  (`ats_terms_of`) et le profil maître validé (409 `profile_required`).
- `save_result` : **idempotent par session**, sous le verrou des comités : une exécution qui n'est
  plus `running` (rejeu après un arrêt, SPEC 9.4) n'est jamais réécrite. Range les votes, le
  verdict, les objections et les changements, passe l'exécution à `done` et, si l'offre a une
  fiche, ajoute l'événement `committee` à son fil, dans la même transaction.

Journaux : identifiants, statuts et nombres seulement (17.2)."""

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

DEFAULT_TITLE = "Poste"


def _analysis(posting: JobPosting, application: Application | None) -> PostingAnalysis:
    """L'analyse rangée de l'offre ; sinon une analyse minimale (intitulé, entreprise, langue).
    Avec une fiche, c'est celle du kit (`kit_language.posting_analysis`, une seule règle)."""
    if application is not None:
        return posting_analysis(posting.analysis, application, posting.text)
    if posting.analysis:
        try:
            return PostingAnalysis.model_validate(posting.analysis)
        except ValidationError:
            pass  # une analyse illisible : le texte de l'offre reste la source
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
                return  # rejeu : l'issue de la session est déjà rangée
            row.votes = [vote.model_dump(mode="json") for vote in votes]
            row.verdict = synthesis.verdict
            row.objections = [o.model_dump(mode="json") for o in synthesis.objections]
            row.changes = [c.model_dump(mode="json") for c in synthesis.changes]
            row.status = "done"
            await self._timeline(db, user_id, row, votes, synthesis)
            await db.commit()
        logger.info(
            "Comité rangé : utilisateur %s, exécution %s, session %s, verdict %s",
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
        """L'événement `committee` de la fiche de l'offre, si elle existe (même transaction)."""
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

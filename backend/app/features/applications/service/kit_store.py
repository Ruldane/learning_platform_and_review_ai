"""Port du kit de candidature (`KitStore`, D142, D143) sur la feature `applications` :
implémentation branchée par `bootstrap_agents.agent_ports(..., kit=...)`. Chaque appel ouvre
ses propres sessions de base, courtes.

- `context` : lecture seule. La fiche (entreprise, intitulé exact, contact), son offre (l'analyse de
  l'offre liée, sinon une analyse minimale de la copie figée de la fiche), le profil maître validé,
  le dossier de `companies` s'il a moins de 30 jours (ses pages **dans l'ordre des citations** :
  `[n]` = rang + 1), la version de CV prête la plus récente de l'offre, les pièces modifiées par
  January (`keep`) et son jour (fuseau de ses réglages). 409 `posting_required` (ni offre ni texte
  figé), 409 `profile_required` (aucun profil validé).
- `save_piece` : **idempotent par `(fiche, pièce, session)`** et sûr sous écritures parallèles (les
  sept branches du parcours rangent en même temps) : un verrou par fiche, puis la ligne unique
  `(fiche, pièce)` ; la ligne de la même session, ou une pièce que January a modifiée entre-temps,
  n'est jamais réécrite. Rangée la dernière pièce de la session, l'événement `kit` « terminé »
  entre au fil, dans la même transaction.
- `save_dossier` : `companies.dossier`, ses pages lues (dans l'ordre) et sa date ; idempotent par
  session (l'identifiant de la session est rangé avec le dossier).

Journaux : identifiants, nombres et statuts seulement, jamais une pièce, l'entreprise, un contact ni
une adresse (17.2)."""

import asyncio
import logging
from datetime import timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.kit_schema import (
    KIT_KINDS,
    CompanyDossier,
    CvVersionRef,
    KitContext,
    KitKind,
    KitStatus,
    SourceRef,
)
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.applications import Application
from app.db.models.postings import Company
from app.features.applications.repository import (
    CompanyRepository,
    ContactRepository,
    EventRepository,
    KitRepository,
)
from app.features.applications.service.kit_language import posting_analysis
from app.features.applications.service.reminders_out import pick_contact
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application
from app.features.cv.service.versions import ready_versions_by_posting, validated_profile
from app.features.postings.service.duplicates import zone_of
from app.features.postings.service.queries import postings_by_ids
from app.features.postings.service.rules import company_key

logger = logging.getLogger(__name__)

DOSSIER_MAX_AGE = timedelta(days=30)
END_TEXT = "Kit de candidature terminé"
GRAPH = "application_kit"
SUBJECT = "application_kit"


def company_name_key(name: str) -> str:
    """La clé de la fiche entreprise d'un nom : `company_key`, sinon le nom en minuscules (un nom
    sans lettre latine donnerait une clé vide). Une seule clé pour lire et écrire le dossier."""
    return company_key(name) or name.strip().casefold()


def posting_required() -> AppError:
    return AppError(
        "posting_required",
        "Cette fiche n'a ni offre ni texte d'offre : ajoute-le avant de préparer le kit.",
        409,
    )


def profile_required() -> AppError:
    return AppError(
        "profile_required", "Valide d'abord ton profil maître : le kit s'appuie sur lui.", 409
    )


def kit_lock(rt: ApplicationsRuntime, user_id: str, application_id: str) -> asyncio.Lock:
    """Un verrou par fiche : lancement, pièces rangées et modifications ne se croisent pas."""
    return rt.locks.get(user_id, f"kit:{application_id}")


async def posting_inputs(
    db: AsyncSession, user_id: str, row: Application
) -> tuple[str, PostingAnalysis]:
    """Le texte de l'offre (la copie figée de la fiche, sinon l'offre liée) et son analyse ;
    409 `posting_required` sans texte."""
    posting = None
    if row.posting_id is not None:
        posting = (await postings_by_ids(db, user_id, [row.posting_id])).get(row.posting_id)
    text = (row.posting_text or (posting.text if posting else "") or "").strip()
    if not text:
        raise posting_required()
    return text, posting_analysis(posting.analysis if posting else None, row, text)


def _dossier_of(
    company: Company | None, fresh: bool
) -> tuple[CompanyDossier | None, list[SourceRef]]:
    """Le dossier repris (de moins de 30 jours) et ses pages, dans l'ordre où elles sont citées."""
    if company is None or not fresh or not company.dossier:
        return None, []
    try:
        dossier = CompanyDossier.model_validate(company.dossier)
        sources = [SourceRef.model_validate(ref) for ref in company.dossier_sources]
    except ValidationError:
        return None, []  # un dossier illisible est refait
    return dossier, sources


class AgentKitStore:
    def __init__(self, runtime: ApplicationsRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, application_id: str) -> KitContext:
        rt = self._rt
        async with rt.session_factory() as db:
            row = await get_application(db, user_id, application_id)
            text, analysis = await posting_inputs(db, user_id, row)
            profile = await validated_profile(db, user_id)
            if profile is None:
                raise profile_required()
            today = local_today(await zone_of(db, user_id), rt.now())
            contact = pick_contact(await ContactRepository(db, user_id).of_application(row.id))
            company = await CompanyRepository(db, user_id).by_key(company_name_key(row.company))
            pieces = await KitRepository(db, user_id).of_application(row.id)
            version = await self._version(db, user_id, row)
        edited = {piece.kind for piece in pieces if piece.edited}
        fresh = (
            company is not None
            and company.dossier_at is not None
            and rt.now() - company.dossier_at < DOSSIER_MAX_AGE
        )
        dossier, sources = _dossier_of(company, fresh)
        return KitContext(
            application_id=row.id,
            language="en" if analysis.language == "en" else "fr",
            today=today,
            posting_text=text,
            analysis=analysis,
            company=row.company,
            title=row.title,
            contact=contact.name if contact else None,
            profile=profile,
            company_dossier=dossier,
            company_dossier_sources=sources,
            cv_version=version,
            keep=[kind for kind in KIT_KINDS if kind in edited],
        )

    async def _version(
        self, db: AsyncSession, user_id: str, row: Application
    ) -> CvVersionRef | None:
        if row.posting_id is None:
            return None
        ready = (await ready_versions_by_posting(db, user_id)).get(row.posting_id)
        return CvVersionRef(version_id=ready[0], number=ready[1]) if ready else None

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str:
        rt = self._rt
        async with kit_lock(rt, user_id, application_id), rt.session_factory() as db:
            app_row = await get_application(db, user_id, application_id)
            repo = KitRepository(db, user_id)
            row = await repo.of_kind(application_id, kind)
            if row is not None and (row.session_id == session_id or row.edited):
                # Rejeu (SPEC 9.4), ou pièce modifiée par January depuis : rien n'est réécrit,
                # mais la pièce compte : la fin du kit s'écrit si elle était la dernière.
                await self._close_if_done(db, user_id, session_id, app_row)
                await db.commit()
                return row.id
            fields = {
                "status": status,
                "content": content,
                "meta": await self._meta(db, user_id, app_row, kind, meta),
                "edited": False,
                "session_id": session_id,
            }
            if row is None:
                row = await repo.add(application_id=application_id, kind=kind, **fields)
            else:
                for name, value in fields.items():
                    setattr(row, name, value)
                row.updated_at = rt.now()
            await db.flush()
            await self._close_if_done(db, user_id, session_id, app_row)
            await db.commit()
            logger.info(
                "Pièce du kit rangée : utilisateur %s, fiche %s, pièce %s, statut %s",
                user_id,
                application_id,
                kind,
                status,
            )
            return row.id

    async def _meta(
        self, db: AsyncSession, user_id: str, row: Application, kind: str, meta: dict[str, Any]
    ) -> dict[str, Any]:
        """Le `meta` de la pièce ; le dossier garde ses pages (`source_refs`, dans l'ordre des
        citations) : elles survivent à un dossier refait plus tard par une autre fiche."""
        stored = dict(meta)
        if kind != "company_brief" or not meta.get("sources"):
            return stored
        company = await CompanyRepository(db, user_id).by_key(company_name_key(row.company))
        if company is not None:
            stored["source_refs"] = [dict(ref) for ref in company.dossier_sources]
        return stored

    async def _close_if_done(
        self, db: AsyncSession, user_id: str, session_id: str, app_row: Application
    ) -> None:
        """Les sept pièces sont rangées (par la session, ou gardées telles quelles) : l'événement
        `kit` « terminé » entre au fil, avec le compte des statuts."""
        if await EventRepository(db, user_id).kit_ended(session_id):
            return
        rows = await KitRepository(db, user_id).of_application(app_row.id)
        mine = [row for row in rows if row.session_id == session_id]
        done = {row.kind for row in rows if row.session_id == session_id or row.edited}
        if done != set(KIT_KINDS):
            return
        counts = [row.status for row in mine]
        kept = len(done) - len(mine)
        text = (
            f"{END_TEXT} : {counts.count('ready')} prête(s), "
            f"{counts.count('to_check')} à vérifier, {counts.count('failed')} en échec"
            + (f", {kept} gardée(s) telle(s) quelle(s)." if kept else ".")
        )
        await EventRepository(db, user_id).add(
            application_id=app_row.id, kind="kit", at=self._rt.now(), text=text, ref_id=session_id
        )

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None:
        rt = self._rt
        key = company_name_key(company)
        async with rt.locks.get(user_id, "kit-dossier"), rt.session_factory() as db:
            repo = CompanyRepository(db, user_id)
            row = await repo.by_key(key) or await repo.add(name=company[:200], name_norm=key[:200])
            if row.dossier and row.dossier.get("session_id") == session_id:
                return  # rejeu : rien à réécrire
            row.dossier = {**dossier.model_dump(mode="json"), "session_id": session_id}
            row.dossier_sources = [source.model_dump(mode="json") for source in sources]
            row.dossier_at = rt.now()
            await db.commit()
            logger.info(
                "Dossier rangé : utilisateur %s, entreprise %s, session %s, %d page(s)",
                user_id,
                row.id,
                session_id,
                len(sources),
            )

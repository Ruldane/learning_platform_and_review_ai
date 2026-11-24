import re
from collections.abc import Collection, Sequence
from datetime import tzinfo
from unicodedata import combining, normalize
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.conversation_port import ConversationReference, ConversationSource
from app.core.clock import user_zone
from app.db.models.conversations import ConversationTurn
from app.db.models.postings import JobPosting
from app.features.applications.service.offers_context import (
    ApplicationFact,
    applications_for_offers_chat,
)
from app.features.gap.service.rows import rows_by_posting
from app.features.gap.service.score import GapRow
from app.features.postings.service.queries import postings_for_chat
from app.features.settings.service import SettingsService

MAX_POSTINGS = 12
MAX_DETAILED = 3
MAX_APPLICATIONS = 2
MAX_CONTACTS = 3
MAX_EXCERPT = 450


def _words(text: str) -> set[str]:
    plain = "".join(char for char in normalize("NFD", text.casefold()) if not combining(char))
    return set(re.findall(r"[^\W_]+", plain))


def _select(
    postings: Sequence[JobPosting], question: str, previous: Collection[str]
) -> list[JobPosting]:
    words = _words(question)

    def rank(posting: JobPosting) -> tuple[int, bool]:
        company = _words(posting.company or "")
        title = _words(posting.title or "")
        relevance = 2 * bool(company and company <= words) + len(title & words)
        return relevance, posting.id in previous

    return sorted(postings, key=rank, reverse=True)[:MAX_POSTINGS]


def _title(posting: JobPosting) -> str:
    title = posting.title or "Untitled posting"
    return f"{title} at {posting.company}" if posting.company else title


def _application_summary(facts: Sequence[ApplicationFact]) -> str:
    if not facts:
        return "No linked application is recorded."
    return ", ".join(
        f"{fact.status} (applied on {fact.applied_on or 'no date recorded'})"
        for fact in facts[:MAX_APPLICATIONS]
    )


def _skills(rows: Sequence[GapRow]) -> str:
    gaps = [row for row in rows if row.level is None and row.action != "out_of_scope"]
    ranked = sorted(gaps, key=lambda row: not row.required)[:6]
    return ", ".join(
        f"{row.skill} ({'required' if row.required else 'optional'})" for row in ranked
    )


def _posting_reference(
    posting: JobPosting,
    zone: tzinfo,
    facts: Sequence[ApplicationFact],
    gaps: Sequence[GapRow],
    detail: bool,
    coverage: str = "",
) -> ConversationReference:
    added = posting.created_at.astimezone(zone).date().isoformat()
    base = f"{coverage}Added: {added}. Linked applications: {_application_summary(facts)}"
    if detail:
        skills = _skills(gaps)
        if skills:
            base += f"\nSkills absent from the profile: {skills}."
        elif not gaps:
            base += "\nNo gap assessment is available."
        base += f"\nOffer excerpt: {posting.text[:MAX_EXCERPT]}"
    source = ConversationSource(
        kind="posting", id=UUID(posting.id), title=_title(posting), excerpt=None
    )
    return ConversationReference(source, base, primary=detail)


def _application_reference(posting: JobPosting, fact: ApplicationFact) -> ConversationReference:
    contacts = "; ".join(
        f"{contact.name} ({contact.role or 'role not recorded'})"
        for contact in fact.contacts[:MAX_CONTACTS]
    )
    material = (
        f"Status: {fact.status}. Applied on: {fact.applied_on or 'no date recorded'}. "
        f"Saved contacts: {contacts or 'none recorded'}."
    )
    source = ConversationSource(
        kind="application",
        id=UUID(fact.id),
        title=f"Application for {_title(posting)}",
        excerpt=None,
    )
    return ConversationReference(source, material, primary=True)


async def offers_references(
    db: AsyncSession, turn: ConversationTurn, history: Sequence[ConversationTurn]
) -> list[ConversationReference]:
    previous = {str(s["id"]) for past in history for s in past.sources if s["kind"] == "posting"}
    postings = await postings_for_chat(db, turn.user_id)
    shown = _select(postings, turn.question, previous)
    detailed = shown[:MAX_DETAILED]
    detailed_ids = {row.id for row in detailed}
    facts = await applications_for_offers_chat(
        db, turn.user_id, {row.id for row in shown}, detailed_ids
    )
    gaps = await rows_by_posting(db, turn.user_id, detailed)
    zone = user_zone((await SettingsService(db, turn.user_id).get()).timezone)
    refs: list[ConversationReference] = []
    for index, posting in enumerate(shown):
        records = facts.get(posting.id, [])
        detail = posting.id in detailed_ids
        coverage = f"Showing {len(shown)} of {len(postings)} saved offers. " if index == 0 else ""
        refs.append(
            _posting_reference(posting, zone, records, gaps.get(posting.id, []), detail, coverage)
        )
        if detail:
            refs.extend(
                _application_reference(posting, fact) for fact in records[:MAX_APPLICATIONS]
            )
    return refs

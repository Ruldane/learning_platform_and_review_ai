"""Linking a record without a posting to the posting that arrives later (SPEC 6.3, D155). A record
entered by hand or in one sentence has no posting; when January pastes the posting and a CV
version is ready, adoption does not create a second record for the same position: it links the
look-alike record without a posting (same link: certain; same company and close job title:
probable), never a record already linked to another posting nor one confirmed as "another
position" (`matching.match`). A posting that looks like another record (already linked, or
"possible") gets no record: the alert on the posting's page remains the way."""

from collections.abc import Sequence
from datetime import date
from zoneinfo import ZoneInfo

from app.db.models.applications import Application
from app.db.models.postings import JobPosting
from app.features.applications.service.check import incoming_from_posting
from app.features.applications.service.matching import match
from app.features.applications.service.views import view_of

LINKABLE = ("certain", "probable")


def target_of(
    posting: JobPosting, rows: Sequence[Application], zone: ZoneInfo, today: date
) -> tuple[Application | None, bool]:
    """`(record to link, looks like another record)`: the record without a posting that best
    matches the posting. Certain hits (same link) come before probable ones: if only records
    already linked to another posting are certain, nothing is linked, even if a record without a
    posting is probable. Otherwise `(None, True)` if another record looks alike (already linked,
    or "possible"), `(None, False)` if nothing looks alike."""
    hits = [
        hit
        for hit in match(incoming_from_posting(posting), [view_of(r, zone) for r in rows], today)
        if hit.level != "info"
    ]
    by_id = {row.id: row for row in rows}
    for level in LINKABLE:  # a certain hit decides alone: never a probable one in its place
        group = [hit for hit in hits if hit.level == level]
        for hit in group:
            row = by_id[hit.application_id]
            if row.posting_id is None:
                return row, True
        if group:
            return None, True  # the same posting is already tracked by a record linked elsewhere
    return None, bool(hits)


def link_posting(row: Application, posting: JobPosting) -> None:
    """The record takes the posting: its id, the frozen text and the link if missing."""
    row.posting_id = posting.id
    if not (row.posting_text or "").strip():
        row.posting_text = posting.text
    if row.url is None:
        row.url, row.url_norm = posting.url, posting.url_norm

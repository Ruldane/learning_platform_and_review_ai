"""Lien d'une fiche sans offre avec l'offre qui arrive plus tard (SPEC 6.3, D155). Une fiche saisie
à la main ou en une phrase n'a pas d'offre ; quand January colle l'offre et qu'une version de CV
est prête, l'adoption ne crée pas une seconde fiche pour le même poste : elle relie la fiche sans
offre qui ressemble (même lien : certain ; même entreprise et intitulé proche : probable), jamais
une fiche déjà liée à une autre offre ni une fiche confirmée « autre poste » (`matching.match`).
Une offre qui ressemble à une autre fiche (déjà liée, ou « possible ») n'a pas de fiche créée :
l'alerte de la page de l'offre reste le chemin."""

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
    """`(fiche à relier, ressemble à une autre fiche)` : la fiche sans offre la plus ressemblante
    de l'offre (niveau certain ou probable) ; sinon `(None, True)` si une autre fiche ressemble
    (déjà liée, ou « possible »), `(None, False)` si rien ne ressemble."""
    hits = [
        hit
        for hit in match(incoming_from_posting(posting), [view_of(r, zone) for r in rows], today)
        if hit.level != "info"
    ]
    by_id = {row.id: row for row in rows}
    for hit in hits:
        row = by_id[hit.application_id]
        if hit.level in LINKABLE and row.posting_id is None:
            return row, True
    return None, bool(hits)


def link_posting(row: Application, posting: JobPosting) -> None:
    """La fiche prend l'offre : son identifiant, le texte figé et le lien s'ils manquent."""
    row.posting_id = posting.id
    if not (row.posting_text or "").strip():
        row.posting_text = posting.text
    if row.url is None:
        row.url, row.url_norm = posting.url, posting.url_norm

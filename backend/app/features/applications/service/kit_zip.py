"""L'archive du kit de candidature (SPEC 6.4, F16, D143) : `Kit_<Entreprise>_<Poste>.zip`.

- un fichier Markdown par pièce rangée, dans l'ordre de F16 : `01_cv.md` … `07_pitch.md` ;
- le PDF de la version de CV prête, sous son nom (`CV_<Nom>_<Entreprise>_<Poste>.pdf`), si la pièce
  `cv` en désigne une ;
- `README.txt` : les pièces « à vérifier » avec leurs raisons, et les pièces omises (absentes ou
  en échec).

Rien n'est envoyé par l'application : January relit puis copie. Journaux : identifiants seulement,
jamais le nom du fichier ni une pièce (17.2)."""

import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime

from app.agents.tools.kit_schema import KIT_TITLES
from app.core.errors import AppError
from app.db.models.applications import KitItem
from app.features.applications.repository import KitRepository
from app.features.applications.schemas_kit import KIT_ORDER
from app.features.applications.service.kit_items import has_blank, item_out
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application
from app.features.cv.service.naming import kit_filename
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.versions import version_pdf
from app.features.portfolio.service.links import approved_link

logger = logging.getLogger(__name__)

README = "README.txt"
_KEPT = ("ready", "to_check")
_FILE_MODE = 0o100644


@dataclass(frozen=True)
class Entry:
    path: str
    title: str
    row: KitItem | None

    @property
    def included(self) -> bool:
        return self.row is not None and self.row.status in _KEPT


def file_name(kind: str) -> str:
    return f"{KIT_ORDER.index(kind) + 1:02d}_{kind}.md"


def _reasons(row: KitItem) -> str:
    item = item_out(row)
    reasons = []
    if item.flags:
        reasons.append("terms absent from your profile: " + ", ".join(item.flags))
    if item.salary_fields:
        reasons.append(f"salary questions to complete: {item.salary_fields}")
    if has_blank(row.kind, row.content) and not item.salary_fields:
        reasons.append("answers to complete")
    return ", ".join(reasons) or "review before use"


def _omitted(entry: Entry) -> str:
    row = entry.row
    if row is not None and row.status == "failed":
        error = str((row.meta or {}).get("error") or "No error details available.")
        return f"- {entry.path} ({entry.title}): failed. {error}"
    return f"- {entry.path} ({entry.title}): not yet generated"


def readme(entries: list[Entry], pdf: str | None, pdf_missing: bool) -> str:
    """Build the included README with review reasons and omitted items."""
    lines = [
        "Application kit",
        "",
        "Review each item before copying it into your application.",
        "",
        "Items to review",
    ]
    to_check = [e for e in entries if e.row is not None and e.row.status == "to_check"]
    lines += [f"- {e.path} ({e.title}): {_reasons(e.row)}" for e in to_check if e.row] or ["- None"]
    lines += ["", "Omitted items"]
    lines += [_omitted(e) for e in entries if not e.included] or ["- None"]
    if pdf:
        lines += ["", f"CV PDF: {pdf}"]
    elif pdf_missing:
        lines += ["", "The ready CV PDF could not be attached."]
    return "\n".join(lines) + "\n"


async def _pdf(cv: CvRuntime, user_id: str, version_id: str) -> tuple[str, bytes] | None:
    try:
        return await version_pdf(cv, user_id, version_id)
    except AppError:
        return None  # The README reports a missing PDF.


def _write(files: list[tuple[str, bytes]], now: datetime) -> bytes:
    stamp = (now.year, now.month, now.day, now.hour, now.minute, now.second)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.external_attr = _FILE_MODE << 16  # fichier ordinaire, rw-r--r--
            archive.writestr(info, data, zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


async def kit_archive(
    rt: ApplicationsRuntime, cv: CvRuntime, user_id: str, application_id: str
) -> tuple[str, bytes]:
    """`(nom ASCII de l'archive, octets)` ; 404 `application_not_found`."""
    async with rt.session_factory() as db:
        app_row = await get_application(db, user_id, application_id)
        rows = await KitRepository(db, user_id).of_application(app_row.id)
        name = kit_filename(app_row.company, app_row.title)
        portfolio = await approved_link(db, user_id, "kit", rt.portfolio_origin())
    pieces = {row.kind: row for row in rows}
    entries = [Entry(file_name(kind), KIT_TITLES[kind], pieces.get(kind)) for kind in KIT_ORDER]
    files = [
        (e.path, e.row.content.rstrip().encode("utf-8") + b"\n")
        for e in entries
        if e.row is not None and e.included
    ]
    cv_row = pieces.get("cv")
    version_id = (cv_row.meta or {}).get("version_id") if cv_row is not None else None
    wanted = bool(version_id) and cv_row is not None and cv_row.status in _KEPT
    pdf = await _pdf(cv, user_id, str(version_id)) if wanted else None
    if pdf is not None:
        files.append(pdf)
    if portfolio is not None:
        files.append(("08_portfolio.txt", (portfolio + "\n").encode()))
    files.append(
        (README, readme(entries, pdf[0] if pdf else None, wanted and pdf is None).encode())
    )
    logger.info(
        "Archive du kit préparée : utilisateur %s, fiche %s, %d fichier(s)",
        user_id,
        application_id,
        len(files),
    )
    return name, _write(files, rt.now())

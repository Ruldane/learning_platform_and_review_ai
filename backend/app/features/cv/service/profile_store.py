"""Port du profil maître vu par l'Archiviste (`ProfileStore`, D124).

`sources` relit chaque PDF rangé par son fichier (jamais les fragments indexés : rien avant
l'indexation, fragments seuls, texte invisible repris ; preflight G6), passe sa mise en page et
garde les blocs visibles dans l'ordre du flux ; les blocs invisibles sont mis de côté pour être
signalés. `save_draft` range le brouillon une seule fois par session, ids repris de la dernière
version validée et jamais réattribués (`profile_merge`).

Journaux : identifiants et nombres seulement, jamais un texte du profil ni d'un document (17.2)."""

import logging
from collections.abc import Sequence

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.profile_port import (
    MAX_HIDDEN_LINES,
    MAX_NOTE_CHARS,
    MAX_SOURCE_CHARS,
    ProfileSource,
    ProfileSources,
    SourceKind,
)
from app.core.errors import AppError
from app.features.cv.repository import ProfileRepository
from app.features.cv.service.profile_merge import all_ids, merge_draft
from app.features.cv.service.runtime import CvRuntime
from app.features.memory.service.document_files import StoredFile, document_file
from app.features.sessions.service import session_facts
from app.providers.pdf.base import MAX_CV_PAGES, MAX_LINKEDIN_PAGES, PdfLayout

logger = logging.getLogger(__name__)

HIDDEN_LINE_MAX = 200


def document_not_found() -> AppError:
    return AppError("document_not_found", "Document not found.", 404)


def not_a_pdf() -> AppError:
    return AppError("profile_source_invalid", "Import the master profile from a PDF.", 422)


def _kind(file: StoredFile) -> SourceKind:
    """LinkedIn s'il est étiqueté ainsi (et pas aussi comme CV), sinon le CV."""
    return "linkedin" if "linkedin" in file.tags and "cv" not in file.tags else "cv"


def _texts(layout: PdfLayout) -> tuple[str, list[str]]:
    """Texte visible (blocs dans l'ordre du flux, une page par paragraphe) et lignes invisibles."""
    pages: list[str] = []
    hidden: list[str] = []
    for page in layout.pages:
        pages.append("\n".join(b.text for b in page.blocks if not b.invisible and b.text.strip()))
        hidden += [b.text.strip()[:HIDDEN_LINE_MAX] for b in page.blocks if b.invisible]
    return "\n\n".join(pages)[:MAX_SOURCE_CHARS], [line for line in hidden if line]


class AgentProfileStore:
    """`ProfileStore` de la composition (`app.bootstrap_career`)."""

    def __init__(self, runtime: CvRuntime) -> None:
        self._rt = runtime

    async def _previous(self, user_id: str) -> MasterProfileData | None:
        async with self._rt.session_factory() as db:
            row = await ProfileRepository(db, user_id).latest("validated")
        return MasterProfileData.model_validate(row.data) if row is not None else None

    async def _read(self, user_id: str, document_id: str) -> tuple[SourceKind, PdfLayout]:
        file = await document_file(self._rt.memory, user_id, document_id)
        if file is None:
            raise document_not_found()
        if file.source_kind != "pdf":
            raise not_a_pdf()
        kind = _kind(file)
        pages = MAX_LINKEDIN_PAGES if kind == "linkedin" else MAX_CV_PAGES
        return kind, await self._rt.layout.extract_layout(file.data, max_pages=pages)

    async def sources(
        self, user_id: str, document_ids: Sequence[str], note: str | None
    ) -> ProfileSources:
        read = [await self._read(user_id, doc_id) for doc_id in dict.fromkeys(document_ids)]
        docs: list[ProfileSource] = []
        hidden: list[str] = []
        for kind, layout in sorted(read, key=lambda pair: pair[0] != "cv"):  # CV d'abord
            text, invisible = _texts(layout)
            docs.append(ProfileSource(kind, text))
            hidden += invisible
        if note is not None and note.strip():
            docs.append(ProfileSource("note", note.strip()[:MAX_NOTE_CHARS]))
        logger.info(
            "Sources du profil : utilisateur %s, %d document(s), %d ligne(s) invisible(s)",
            user_id,
            len(read),
            len(hidden),
        )
        return ProfileSources(docs, await self._previous(user_id), hidden[:MAX_HIDDEN_LINES])

    async def save_draft(
        self, user_id: str, session_id: str, draft: MasterProfileData, dropped: Sequence[str]
    ) -> int:
        async with self._rt.version_lock(user_id), self._rt.session_factory() as db:
            repo = ProfileRepository(db, user_id)
            existing = await repo.by_session(session_id)
            if existing is not None:
                return existing.version
            facts = await session_facts(db, user_id, session_id)
            document_ids = facts.input.get("document_ids", []) if facts is not None else []
            rows = await repo.all_versions()
            versions = [MasterProfileData.model_validate(row.data) for row in rows]
            validated = next((row for row in rows if row.status == "validated"), None)
            previous = MasterProfileData.model_validate(validated.data) if validated else None
            data = merge_draft(draft, previous, all_ids(versions))
            version = (rows[0].version if rows else 0) + 1
            await repo.add(
                version=version,
                status="draft",
                data=data.model_dump(mode="json"),
                source="archivist",
                session_id=session_id,
                document_ids=[str(doc_id) for doc_id in document_ids],
                dropped=list(dropped),
            )
            await db.commit()
        logger.info(
            "Brouillon du profil : utilisateur %s, session %s, version %d",
            user_id,
            session_id,
            version,
        )
        return version
